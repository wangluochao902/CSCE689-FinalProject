from flask import Flask, render_template, request, jsonify, abort
from flask_cors import CORS
import os
from gradient_infill.process import process_gcode, InfillType
from gradient_infill.defaults import CURA_ENGINE_COMMAND
import subprocess

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.mkdir(TMP_DIR) if not os.path.exists(TMP_DIR) else None

app = Flask(__name__)
app.config.from_object(__name__)
logger = app.logger

# enable CORS
CORS(
    app,
    resources={
        r"/*": {
            "origins":
            #  'https://wangluochao902.github.io'
            "*"
        }
    },
)


@app.route("/")
def hello_world():
    name = os.environ.get("NAME", "World")
    return "Hello {}!".format(name)


@app.route("/gradientInfill", methods=["GET", "POST"])
def gradientInfill():
    stl_file, gradient_setting, print_setting = (
        request.json["stl_file"],
        request.json["gradient_setting"],
        request.json["print_setting"],
    )
    needed_keys = {"max_flow", "min_flow", "enable_gradient", "infill_targets", "gradient_discretization"}

    for key in needed_keys:
        if key not in gradient_setting:
            return f"Missing key {key} in gradient_setting", 500

    if set(gradient_setting.keys()) != needed_keys:
        return (
            f"Some setting keys of {' '.join(list(needed_keys))} are not given or other setting are given",
            500,
        )

    special_print_setting_keys = [
        "infill_sparse_density",
        "disable_top_bottom_layers",
        "other_setting_string"]
    normal_print_setting_keys = [
        "infill_pattern",
        "adhesion_type",
        "retraction_enable",
        "retraction_enable",
        "speed_print",
        "speed_infill",
        "speed_wall",
        "material_print_temperature",
        "material_print_temperature_layer_0",
        "material_initial_print_temperature",
        "material_final_print_temperature",
        "material_bed_temperature",
        "material_bed_temperature_layer_0"
    ]
    for key in special_print_setting_keys + normal_print_setting_keys:
        if key not in print_setting:
            return f"Missing key {key} in print_seting", 500

    stl_path = os.path.join(TMP_DIR, "stl_file.stl")
    gcode_out_path = os.path.join(TMP_DIR, "gcode_out.gcode")
    processed_gcode_path = os.path.join(TMP_DIR, "processed_gcode.gcode")

    final_gcode_path = gcode_out_path

    with open(stl_path, "w") as f:
        f.write(stl_file)
    infill_sparse_density = print_setting["infill_sparse_density"]
    infill_line_width = 0.4
    if infill_sparse_density == 0:
        infill_line_distance = 0
    else:
        infill_line_distance = (infill_line_width * 100) / infill_sparse_density

    if print_setting["infill_pattern"] not in ("lines", "grid", "gyroid"):
        return f"Only 'lines' and 'gyroid' infill pattern are supported", 500

    print_setting_string = f'-s infill_line_distance={infill_line_distance}'

    if print_setting["disable_top_bottom_layers"]:
        print_setting_string += (
            " -s top_layers=0 -s bottom_layers=0"
        )
    print_setting_string = ' '.join([print_setting_string] + [f'-s {key}={print_setting[key]}' for key in normal_print_setting_keys])
    print_setting_string += ' ' + print_setting["other_setting_string"]
    print_setting_string = print_setting_string.replace("=True", "=true")
    print("\n\n\nall the print setting is: ", print_setting_string, "\n\n\n")
    p = subprocess.Popen(
        [
            f"{CURA_ENGINE_COMMAND} {print_setting_string} -l {stl_path} -o {gcode_out_path}"
        ],
        shell=True,
    )

    p_status = p.wait()
    # we are using ender 3. In the machine definition file, its ``machine_width=220`` and ``machine_depth=220``
    # So the center is [110, 110]`

    if print_setting["infill_pattern"] in ("lines", "grid"):
        infill_type = InfillType.LINEAR
    else:
        infill_type = InfillType.SMALL_SEGMENTS
    if gradient_setting["infill_targets"]:
        for target in gradient_setting["infill_targets"]:
            target[0] += 110
            target[1] += 110
        process_gcode(
            gcode_out_path,
            processed_gcode_path,
            infill_type=infill_type,
            **gradient_setting,
        )
        final_gcode_path = processed_gcode_path
    with open(final_gcode_path, "r") as f:
        gcode = f.read()
    return jsonify({"gradient_gcode": gcode})


if __name__ == "__main__":
    # use 0.0.0.0 to use it in container
    app.run(host="0.0.0.0", debug=True, port=5000)
