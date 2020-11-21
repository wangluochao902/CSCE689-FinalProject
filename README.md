# CSCE689-FinalProject
# Interactive Infill Reinforcement - Backend

## Team members
Nelson Dsouza - Front-end development

Luochao Wang - Back-end development

### General information
This project contains 2 components:
  
  1. Three JS interactive webpage (Front-end): can be found @ [Github Link](https://github.tamu.edu/dso-nelson/CSCE689-Final-Team-Pumpkin).
  2. CuraEngine and Python postprocessing Server (Back-end): contents are in this repository.

## Get Started
### Local server development (require docker installed)
  1. Clone the repo `git clone https://github.com/wangluochao902/CSCE689-FinalProject.git`
  2. `cd CSCE689-FinalProjec`
  3. Build image `cura` using the dockerfile `docker build . -t cura`
  4. Start a container by `docker run -it cura -p 5000:5000`
  5. Now you backend is started at `http:127.0.0.1:5000`. You can change the url in frontend for communication, e.g. `http://127.0.0.1:5000/gradientInfill` 
  An example for talking to backend server from the frontend:
  ```
  // Read a local stl model and send it the the backend.
  // The backend server will process the stl file and return the processed Gcode.
  const axios = require("axios");
var fs = require("fs");
fs.readFile(
  "D:\\courses\\csce689\\final\\backend\\main\\SingleDisk.stl",
  "utf-8",
  (error, data) => {
    if (error) throw error;
    axios({
      method: "POST",
      // url: "http://127.0.0.1:5000/gradientInfill",
      url: "https://gradient-z6uig4pceq-uc.a.run.app/gradientInfill",
      headers: { "Content-Type": "application/json" },
      data: {
        gradient_setting: {
          max_flow: 550,
          min_flow: 100,
          enable_gradient: true,
          infill_targets: [
            [
              -9.125003333992183,
              15.624632510615706,
              1.0372603919879744,
              10,
              10,
            ],
            [11.973183042705697, 8.14289606298471, 3.794098643118691, 4, 20],
            [
              -13.128027255861639,
              -11.091992474719191,
              4.6762868834805085,
              3,
              5,
            ],
          ],
        },
        print_setting: {
          infill_sparse_density: 40,
          infill_pattern: "gyroid",
          disable_top_bottom_layers: true,
          adhesion_type: "Skirt",
          retraction_enable: true,
          retraction_amount: 6.5, // This is Retraction Distance
          speed_print: 50,
          speed_infill: 50,
          speed_wall: 25,
          material_print_temperature: 210,
          material_print_temperature_layer_0: 210, // this is Printing Temperature Initial Layer
          material_initial_print_temperature: 210, // this is Initial Printing Temperature
          material_final_print_temperature: 210, // this is material_final_print_temperature Final Printing Temperature
          material_bed_temperature: 60, // this is Build Plate Temperature
          material_bed_temperature_layer_0: 60, // this is Build Plate Temperature Initial Layer
          other_setting_string: "-s retraction_speed=25 -s speed_travel=150 -s initial_bottom_layers=1"
        },
        stl_file: data,
      },
    }).then((res) => {
      // console.log(res.data.gradient_gcode)
      fs.writeFile(
        "D:\\courses\\csce689\\final\\backend\\main\\js_gradient1.gcode",
        res.data.gradient_gcode,
        (error) => {
          if (error) throw error;
        }
      );
    }).catch(err => {
      if (err.response) {
        console.log(err.response.data)
      }
  });
  }
);
  ```
### Deploy to the cloud (We use the Cloud Run service at Google Cloud Platform)
