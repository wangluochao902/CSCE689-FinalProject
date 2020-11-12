
# from gradient_infill.process import InfillType

# INFILL_TYPE = InfillType.SMALL_SEGMENTS

# MAX_FLOW = 350.0  # maximum extrusion flow
# MIN_FLOW = 50.0  # minimum extrusion flow
# GRADIENT_THICKNESS = 4.0  # thickness of the gradient (max to min) in mm
# GRADIENT_DISCRETIZATION = 4.0  # only applicable for linear infills; number of segments within the
# # gradient(segmentLength=gradientThickness / gradientDiscretization); use sensible values to not overload the printer

# DEFAULT_GRADIENT_SETTING = {
#     'max_flow': 350.0,
#     'min_flow': 50.0,
#     'gradient_thickness': 18,
#     'gradient_discretization': 4
# }


CURA_ENGINE_COMMAND = "/CuraEngine/build/CuraEngine slice -p -j /CuraEngine/main/fdmprinter.def.json -j /CuraEngine/main/creality_base.def.json -j /CuraEngine/main/creality_ender3.def.json -j /CuraEngine/main/fdmextruder.def.json -j /CuraEngine/main/creality_base_extruder_0.def.json  -s relative_extrusion=true -s center_object=true -s layer_height=0.2"