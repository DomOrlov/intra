import os
import sunpy.map
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from astropy.visualization import AsymmetricPercentileInterval, ImageNormalize, SqrtStretch
from astropy import units as u
import numpy as np
from astropy.coordinates import SkyCoord
from sunpy.physics.differential_rotation import solar_rotate_coordinate
from datetime import datetime, timedelta
import glob

test_mode = False
test_file = "aligned_eis_2014_02_01__10_50_35_intensity.fits"

eis_directory = r"C:\Users\domor\gazelle\demreg_FIP\aligned_fe12_maps"
intensity_directory = r"C:\Users\domor\gazelle\demreg_FIP\intensity_maps"
aia_directory = r"C:\Users\domor\gazelle\demreg_FIP\tmp"
output_directory = r"C:\Users\domor\gazelle\demreg_FIP\overlayed_images"
# Define the original base center and cropping dimensions
original_time = "2014-01-29T20:00:08.22"

# Loop through all .fits files in the EIS directory or just the test file if in test mode
if test_mode:
    eis_files = [test_file]
else:
    eis_files = [f for f in os.listdir(eis_directory) if f.endswith('.fits')]

for eis_file in eis_files:
    if not eis_file.endswith('.fits'):
        continue

    # Extract date, time, element, and number from the filename
    filename_parts = eis_file.replace('aligned_', '').replace('.fits', '').split('__')
    if len(filename_parts) != 2:
        print(f"Unexpected filename format: {eis_file}. Expected format: 'aligned_YYYY_MM_DD__HH_MM_SS_element_number.fits'")
        continue

    date = filename_parts[0].replace('eis_', '')  # Removes 'eis_' to get '2014_02_02'
    time_and_element = filename_parts[1].split('_')
    time = '_'.join(time_and_element[:3])  # '14_19_52'
    element = '_'.join(time_and_element[3:-1])  # 'ar11188'
    number = time_and_element[-1]  # '81'
    

    print(f"Processing EIS file: {eis_file}")
    print(f"Element: {element}, Date: {date}, Time: {time}")

    # Parse the EIS observation time
    eis_time = datetime.strptime(f"{date}T{time}", "%Y_%m_%dT%H_%M_%S")

    # Round to the nearest minute with seconds set to 00
    rounded_time = eis_time.replace(second=0, microsecond=0)

    # Use glob to match any file with the same date and time (HH_MM), ignoring seconds/milliseconds
    pattern = os.path.join(aia_directory, f"aia.lev1.193A_{rounded_time.strftime('%Y_%m_%dT%H_%M')}_*Z.image_lev1.fits")

    # Find matching files locally
    matching_files = glob.glob(pattern)

    # Output the search pattern and matching files for debugging
    print(f"Search pattern used: {pattern}")
    print(f"Matching files found: {matching_files}")

    # Check if a suitable AIA file was found
    if not matching_files:
        print(f"No suitable AIA file found for {eis_file}. Skipping.")
        continue

    # Load the corresponding aligned Fe XII map for header extraction
    fe12_filename = eis_file  # Use the same filename to find the aligned map
    fe12_fit_path = os.path.join(eis_directory, fe12_filename)
    
    try:
        fe12_map = sunpy.map.Map(fe12_fit_path)
        header_fe12 = fe12_map.meta
        print(f"Loaded Fe XII 195.12 Å header from {fe12_fit_path}")
    except Exception as e:
        print(f"Error loading Fe XII map for {fe12_fit_path}: {e}")
        continue    

    # Select the first match (as we do in the alignment script)
    closest_aia_file = matching_files[0]

    # Check if a suitable AIA file was found
    if not closest_aia_file:
        print(f"No suitable AIA file found for {eis_file}. Skipping.")
        continue

    aia_path = os.path.join(aia_directory, closest_aia_file)
    aia_map = sunpy.map.Map(aia_path)
    eis_path = os.path.join(eis_directory, eis_file)

    print(f"Using AIA file {closest_aia_file} for {eis_file}.")

    # Construct a pattern to match all intensity files with the same date and time
    intensity_pattern = os.path.join(intensity_directory, f"{date}__{time}_*.fits")

    # Find all matching intensity files
    matching_intensity_files = glob.glob(intensity_pattern)

    # Output the search pattern and matching files for debugging
    print(f"Intensity search pattern: {intensity_pattern}")
    print(f"Matching intensity files found: {matching_intensity_files}")

    # Check if there are any matching intensity files
    if not matching_intensity_files:
        print(f"No intensity maps found for {date} {time}. Skipping.")
        continue

    # Loop through all matching intensity files
    for intensity_path in matching_intensity_files:
        try:
            intensity_map = sunpy.map.Map(intensity_path)
            intensity_data = intensity_map.data
            print(f"Loaded intensity map data from {intensity_path}")
        except Exception as e:
            print(f"Error loading intensity map for {intensity_path}: {e}")
            continue

        # Combine the header of the aligned Fe XII map with the data of the intensity map
        combined_map = sunpy.map.Map(intensity_data, header_fe12)

        # Use combined_map in place of eis_map
        eis_map = combined_map

        # Extract the element from the intensity file name dynamically
        # Extract the element from the intensity file name dynamically
        intensity_filename = os.path.basename(intensity_path).replace('.fits', '')
        intensity_parts = intensity_filename.split('_')

        # Extract the element based on the expected index (index 7 for the element in the expected filename format)
        element = intensity_parts[7] if len(intensity_parts) > 7 else "Unknown"
        print(f"Processing element: {element}")

        # Define the original base center with the correct coordinate frame and observer
        original_center = SkyCoord(
            (-600 + -1050) / 2 * u.arcsec, 
            (0 - 350) / 2 * u.arcsec, 
            frame='helioprojective',
            obstime=original_time,
            observer='earth'  # Explicitly set the observer
        )

        print(f"Original center (before rotation): {original_center}")

        # Rotate the original center to the new EIS observation time
        rotated_center = solar_rotate_coordinate(original_center, time=eis_map.date)

        print(f"Rotated center: {rotated_center}")

        # Define a dynamic margin around the EIS FOV
        margin = 150 * u.arcsec

        # Dynamically adjust the cropping to fit the EIS FOV with the margin
        new_bottom_left = SkyCoord(eis_map.bottom_left_coord.Tx - margin, 
                                eis_map.bottom_left_coord.Ty - margin, 
                                frame=aia_map.coordinate_frame)
        new_top_right = SkyCoord(eis_map.top_right_coord.Tx + margin, 
                                eis_map.top_right_coord.Ty + margin, 
                                frame=aia_map.coordinate_frame)

        print(f"Dynamic cropping coordinates - Bottom-left: {new_bottom_left}, Top-right: {new_top_right}")

        # Crop the AIA map using the new coordinates
        cropped_aia_map = aia_map.submap(new_bottom_left, top_right=new_top_right)

        # Plotting the cropped AIA image with EIS FOV contour
        plt.figure(figsize=(10, 8))
        ax = plt.subplot(projection=cropped_aia_map)

        # Extract the element from the intensity file name dynamically
        element = intensity_parts[7] if len(intensity_parts) > 7 else "Unknown"
        print(f"Processing element: {element}")


        # Display the cropped AIA map
        norm = ImageNormalize(cropped_aia_map.data, AsymmetricPercentileInterval(1, 99))
        cropped_aia_map.plot(axes=ax, norm=norm, title=f'Overlayed AIA 193 Å - {element} - {date} {time}')

        # Draw a rectangle around the EIS FOV
        bottom_left = eis_map.bottom_left_coord
        top_right = eis_map.top_right_coord

        print(f"EIS map coordinates - Bottom-left: {bottom_left}, Top-right: {top_right}")

        # Convert world coordinates to pixel coordinates
        bl_pixel = cropped_aia_map.world_to_pixel(bottom_left)
        tr_pixel = cropped_aia_map.world_to_pixel(top_right)

        print(f"Rectangle pixel coordinates - Bottom-left: {bl_pixel}, Top-right: {tr_pixel}")

        # Draw rectangle
        rect = Rectangle((bl_pixel.x.value, bl_pixel.y.value), 
                        tr_pixel.x.value - bl_pixel.x.value, 
                        tr_pixel.y.value - bl_pixel.y.value, 
                        edgecolor='red', facecolor='none', linestyle='--', linewidth=2)
        ax.add_patch(rect)

        ## Update the plot title to include the element before saving
        #ax.set_title(f'Overlayed AIA 193 Å - {element} - {date} {time}')

        # Save the plot to the output directory with a unique filename including the element
        output_filename = f'overlayed_{date}__{time}_{element}.png'

        output_path = os.path.join(output_directory, output_filename)
        plt.savefig(output_path)
        plt.close()

        print(f"Saved overlayed image to {output_path}\n")


