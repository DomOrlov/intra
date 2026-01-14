#!/usr/bin/env python
import argparse
import os
import shutil
from ashmcmc import ashmcmc
import matplotlib
matplotlib.use("Agg")  

def make_fe12_intensity_map(filename, ncpu=4):
    """
    Generate intensity map only for Fe XII 195.12 line.
    """
    a = ashmcmc(filename, ncpu=ncpu)
    print(f"DEBUG: ashmcmc outdir => {a.outdir}")

    # Temporary output directory (where ashmcmc will generate files)
    temp_intensity_dir = r"C:\Users\domor\gazelle\demreg_FIP\temp_intensity_maps"
    
    # Desired output directory
    custom_intensity_dir = r"C:\Users\domor\gazelle\demreg_FIP\fe12_intensity_maps"
    
    # Fe XII 195.12 line
    fe12_line = "fe_12_195.12"

    print(f"\Generating intensity map for {fe12_line} in {filename}")
    try:
        m = a.ash.get_intensity(
            fe12_line,
            outdir=temp_intensity_dir,  
            refit=False,
            plot=True,
            mcmc=False,
            calib=True,
            calib_year="2014"
        )

        #print(f"DEBUG: Intensity Stats for {fe12_line} -> Min={m.data.min()}, Max={m.data.max()}, Mean={m.data.mean()}")
        #print(f"DEBUG: Nonzero pixel count for {fe12_line}: {m.data.nonzero()[0].size}")

        #print("============================================")
        #print(f"Saved intensity map for line={fe12_line} in file={filename}")
        #print(f"Temporary output location: {temp_intensity_dir}")
        #print("============================================")

    except Exception as e:
        print(f"Error generating intensity for line={fe12_line} in {filename}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate intensity maps only for Fe XII 195.12 line.")
    parser.add_argument('-c', '--cores', type=int, default=4, help='Number of cores to use.')
    args = parser.parse_args()

    # Temporary output directory
    temp_intensity_dir = r"C:\Users\domor\gazelle\demreg_FIP\temp_intensity_maps"
    
    # Final output directory
    custom_intensity_dir = r"C:\Users\domor\gazelle\demreg_FIP\fe12_intensity_maps"

    # Ensure directories exist
    os.makedirs(temp_intensity_dir, exist_ok=True)
    os.makedirs(custom_intensity_dir, exist_ok=True)

    # Read filenames from config.txt
    try:
        with open("config.txt", "r", encoding="utf-8", newline="") as file:
            filenames = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("ERROR: config.txt not found")
        return

    for filename_full in filenames:
        filename = filename_full.replace(" [processing]", "").replace(" [processed]", "")
        if not filename:
            continue

        print(f"\n==========\nProcessing file: {filename}\n==========")
        try:
            make_fe12_intensity_map(filename, ncpu=args.cores)
        except Exception as e:
            print(f"Error while making intensity map for {filename}: {e}")

    # Batch move all generated files to the final directory
    for root, _, files in os.walk(temp_intensity_dir):
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(custom_intensity_dir, file)
            try:
                shutil.move(src_file, dst_file)
                print(f"Moved {src_file} to {dst_file}")
            except Exception as e:
                print(f"Error moving file {src_file}: {e}")

    print(f"\nFinished processing Fe XII 195.12 intensity maps.")
    print(f"Maps saved to {custom_intensity_dir}")

if __name__ == "__main__":
    main()
