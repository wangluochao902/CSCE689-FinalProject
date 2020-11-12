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

@app.route('/')
def hello_world():
    name = os.environ.get('NAME', 'World')
    return 'Hello {}!'.format(name)


@app.route("/gradientInfill", methods=["GET", "POST"])
def checkcommand():
    stl_file, gradient_setting, print_setting = (
        request.json["stl_file"],
        request.json["gradient_setting"],
        request.json["print_setting"],
    )
    needed_keys = {
        "max_flow",
        "min_flow",
        "enable_gradient",
        "infill_targets",
    }
    if set(gradient_setting.keys()) != needed_keys:
        return (
            f"Some setting keys of {''.join(list(needed_keys))} are not given or other setting are given",
            500,
        )

    if "infill_sparse_density" not in print_setting:
        return f"Missing 'infill_sparse_density'", 500

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

    print_setting_string = (
        f'-s infill_line_distance={infill_line_distance}'
    )
    p = subprocess.Popen(
        [
            f"{CURA_ENGINE_COMMAND} {print_setting_string} -l {stl_path} -o {gcode_out_path}"
        ],
        shell=True,
    )
    # p = subprocess.Popen([f"ls /root"], )
    p_status = p.wait()
    # we are using ender 3. In the machine definition file, its ``machine_width=220`` and ``machine_depth=220``
    # So the center is [110, 110]`
    if gradient_setting["infill_targets"]:
        for target in gradient_setting['infill_targets']:
            target[0] += 110
            target[1] += 110
        process_gcode(
            gcode_out_path,
            processed_gcode_path,
            infill_type=InfillType.SMALL_SEGMENTS,
            **gradient_setting,
        )
        final_gcode_path = processed_gcode_path
    with open(final_gcode_path, "r") as f:
        gcode = f.read()
    return jsonify({"gradient_gcode": gcode})

if __name__ == "__main__":
    # use 0.0.0.0 to use it in container
    app.run(host='0.0.0.0', debug=True, port=5000)