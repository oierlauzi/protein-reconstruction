import configargparse
import numpy as np
from cryoem.projections import generate_2D_projections


parser = configargparse.ArgParser(default_config_files=["protein.config"], 
                                  description="Generator of 2D projections of 3D Cryo-Em volumes")
parser.add("--config-file", "-conf", help='Config file path', 
            required=True, is_config_file=True)
parser.add("--input-file","-in", help="Input file of 3D volume (*.mrc format)", 
            type=str)
parser.add("--projections-num", "-num", help="Number of 2D projections. Default 5000", 
            type=int, default=5000)
parser.add("--angle-shift", "-shift", help="Get the start Euler angles that will rotate around axes Z, Y, Z repsectively. Example usage: -shift 0.0 -shift 0.0 -shift 0.0", 
            action="append", type=float)
parser.add("--angle-coverage", "-cov", help="The range (size of the interval) of the Euler angles aroung Z, Y, Z axes respectively. Example usage: -cov 0.0 -cov 0.0 -cov 0.0", 
            action="append", type=float)
parser.add("--angles-gen-mode", "-ang-gen", help="Specify the mode of generating angles [uniform_S3, uniform_angles]")
parser.add("--output-file", "-out", help="Name of output file containing projections with angles (with the extension)")
args = parser.parse_args()

print("----------")
print(parser.format_values())
print("----------")

generate_2D_projections(input_file_path=args.input_file, 
                        ProjNber=args.projections_num,
                        AngCoverage=args.angle_coverage,
                        AngShift=args.angle_shift,
                        angles_gen_mode=args.angles_gen_mode,
                        output_file_name= args.output_file if args.output_file != "null" else None )
