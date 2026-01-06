
import os
import zipfile
import sys
import argparse
import time

def zip_deterministically(source_dir, output_file):
    """
    Zips the contents of source_dir into output_file deterministically.
    - Sorts file names.
    - Sets timestamps to a fixed epoch (2020-01-01 00:00:00).
    - Sets permissions to 0o644 for files and 0o755 for executables/dirs.
    """
    
    # Fixed timestamp: Jan 1, 2020
    fixed_time = (2020, 1, 1, 0, 0, 0)
    
    # Create the zip file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Walk the directory
        for root, dirs, files in os.walk(source_dir):
            # Sort directories and files for deterministic order
            dirs.sort()
            files.sort()
            
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                
                # Normalize path separators
                rel_path = rel_path.replace(os.path.sep, '/')
                
                # Get file info
                info = zipfile.ZipInfo(rel_path)
                info.date_time = fixed_time
                info.compress_type = zipfile.ZIP_DEFLATED
                
                # Set permissions (external_attr)
                # Unix permissions are in the top 16 bits of external_attr.
                # 0o100644 is standard file (0x81A4 << 16)
                # We can just set standard 644 for files, 755 if executable
                if os.access(abs_path, os.X_OK):
                    # 0o100755
                    info.external_attr = 0o100755 << 16
                else:
                    # 0o100644
                    info.external_attr = 0o100644 << 16

                # Read and write file
                with open(abs_path, 'rb') as f:
                    zf.writestr(info, f.read())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Zip Packager")
    parser.add_argument("source_dir", help="Directory to zip")
    parser.add_argument("output_file", help="Output zip file path")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.source_dir):
        print(f"Error: Source directory '{args.source_dir}' does not exist.")
        sys.exit(1)
        
    try:
        zip_deterministically(args.source_dir, args.output_file)
        print(f"Successfully created deterministic zip: {args.output_file}")
    except Exception as e:
        print(f"Error creating zip: {e}")
        sys.exit(1)
