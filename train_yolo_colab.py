"""
Train a YOLOv8 model on the Mussel Dataset 1 in Google Colab.

This script:
1. Sets up Colab environment (installs ultralytics, mounts Drive if needed)
2. Converts Pascal VOC XML annotations to YOLO format
3. Creates a dataset.yaml file
4. Trains a small YOLOv8n (nano) model

Usage in Colab:
    1. Upload your "Mussel Dataset 1" folder to Colab (or mount Google Drive)
    2. Run this script in a Colab cell
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

# Check if running in Colab
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    print("="*60)
    print("Running in Google Colab")
    print("="*60)
    
    # Install ultralytics
    print("\n[Setup] Installing ultralytics...")
    os.system("pip install ultralytics -q")
    
    # Mount Google Drive (optional - uncomment if dataset is on Drive)
    # from google.colab import drive
    # drive.mount('/content/drive')
    
    print("✓ Setup complete!\n")

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed. Install it with:")
    print("  pip install ultralytics")
    exit(1)


def convert_voc_to_yolo(xml_path, output_dir, class_mapping):
    """
    Convert Pascal VOC XML annotation to YOLO format.
    
    Args:
        xml_path: Path to XML file
        output_dir: Directory to save YOLO .txt file
        class_mapping: Dict mapping class names to class IDs (e.g., {'live': 0, 'dead': 1})
    
    Returns:
        Path to created YOLO .txt file or None if failed
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Get image dimensions
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)
        
        # Create output file
        xml_name = Path(xml_path).stem
        txt_path = output_dir / f"{xml_name}.txt"
        
        yolo_annotations = []
        
        # Process each object
        for obj in root.findall('object'):
            class_name = obj.find('name').text
            if class_name not in class_mapping:
                print(f"Warning: Unknown class '{class_name}' in {xml_path}, skipping")
                continue
            
            class_id = class_mapping[class_name]
            bbox = obj.find('bndbox')
            
            # Get bounding box coordinates
            xmin = float(bbox.find('xmin').text)
            ymin = float(bbox.find('ymin').text)
            xmax = float(bbox.find('xmax').text)
            ymax = float(bbox.find('ymax').text)
            
            # Convert to YOLO format (normalized center x, center y, width, height)
            center_x = (xmin + xmax) / 2.0 / img_width
            center_y = (ymin + ymax) / 2.0 / img_height
            width = (xmax - xmin) / img_width
            height = (ymax - ymin) / img_height
            
            yolo_annotations.append(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}")
        
        # Write YOLO annotation file
        if yolo_annotations:
            with open(txt_path, 'w') as f:
                f.write('\n'.join(yolo_annotations))
            return txt_path
        else:
            # Create empty file if no annotations
            txt_path.touch()
            return txt_path
            
    except Exception as e:
        print(f"Error converting {xml_path}: {e}")
        return None


def prepare_yolo_dataset(dataset_dir, output_dir):
    """
    Convert Pascal VOC dataset to YOLO format.
    
    Args:
        dataset_dir: Path to "Mussel Dataset 1" directory
        output_dir: Directory to create YOLO dataset structure
    """
    dataset_path = Path(dataset_dir)
    output_path = Path(output_dir)
    
    # Class mapping (YOLO uses numeric IDs)
    class_mapping = {
        'live': 0,
        'dead': 1
    }
    
    # Create YOLO dataset structure
    for split in ['train', 'valid', 'test']:
        split_dir = dataset_path / split
        if not split_dir.exists():
            print(f"Warning: {split} directory not found, skipping")
            continue
        
        # Create directories
        images_dir = output_path / split / 'images'
        labels_dir = output_path / split / 'labels'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all XML files
        xml_files = list(split_dir.glob('*.xml'))
        print(f"\nProcessing {split} split: {len(xml_files)} XML files")
        
        converted = 0
        for xml_file in xml_files:
            # Convert annotation
            txt_path = convert_voc_to_yolo(xml_file, labels_dir, class_mapping)
            if txt_path:
                # Copy image file
                img_name = xml_file.stem + '.jpg'
                img_source = split_dir / img_name
                if img_source.exists():
                    img_dest = images_dir / img_name
                    shutil.copy2(img_source, img_dest)
                    converted += 1
                else:
                    print(f"Warning: Image not found for {xml_file}")
        
        print(f"  Converted {converted} images and annotations")
    
    # Create dataset.yaml file (use absolute path for Colab)
    abs_output_path = output_path.absolute()
    yaml_content = f"""# Mussel Detection Dataset
# Classes: live (0), dead (1)

path: {abs_output_path}
train: train/images
val: valid/images
test: test/images

# Classes
names:
  0: live
  1: dead

nc: 2
"""
    
    yaml_path = output_path / 'dataset.yaml'
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    
    print(f"\n✓ Dataset prepared at: {output_path}")
    print(f"✓ Dataset config: {yaml_path}")
    
    return yaml_path


def train_yolo_model(yaml_path, epochs=50, imgsz=416, batch=16, device='cuda'):
    """
    Train a YOLOv8n (nano) model.
    
    Args:
        yaml_path: Path to dataset.yaml file
        epochs: Number of training epochs
        imgsz: Image size for training
        batch: Batch size
        device: Device to use ('cpu', 'cuda', 'mps', or '0' for GPU 0)
    """
    print(f"\n{'='*60}")
    print("Starting YOLOv8 Training")
    print(f"{'='*60}")
    print(f"Dataset: {yaml_path}")
    print(f"Epochs: {epochs}")
    print(f"Image size: {imgsz}")
    print(f"Batch size: {batch}")
    print(f"Device: {device}")
    print(f"{'='*60}\n")
    
    # Load YOLOv8n model (nano - smallest and fastest)
    print("Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')  # Will download if not present
    
    # Train the model
    print("Starting training...")
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project='runs/detect',
        name='mussel_yolo',
        patience=50,  # Early stopping patience
        save=True,
        plots=True,
        verbose=True
    )
    
    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    print(f"Best model saved at: {model.trainer.best}")
    print(f"Results directory: runs/detect/mussel_yolo")
    print(f"\nTo download the model, use:")
    print(f"  from google.colab import files")
    print(f"  files.download('{model.trainer.best}')")
    print(f"{'='*60}\n")
    
    return model.trainer.best


def main():
    """Main training pipeline"""
    # Paths - adjust these for Colab
    if IN_COLAB:
        # In Colab, dataset might be in /content/ or /content/drive/MyDrive/
        # Adjust these paths based on where you upload the dataset
        dataset_dir = Path("/content/Mussel Dataset 1")
        
        # If dataset is on Google Drive (after mounting):
        # dataset_dir = Path("/content/drive/MyDrive/Mussel Dataset 1")
        
        # If dataset is uploaded to Colab's file system:
        # dataset_dir = Path("/content/Mussel Dataset 1")
    else:
        dataset_dir = Path("Mussel Dataset 1")
    
    yolo_dataset_dir = Path("/content/yolo_dataset") if IN_COLAB else Path("yolo_dataset")
    
    # Check if dataset exists
    if not dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {dataset_dir}")
        print("\nTo fix this in Colab:")
        print("1. Upload your 'Mussel Dataset 1' folder to Colab:")
        print("   - Click the folder icon on the left sidebar")
        print("   - Click 'Upload' and select your dataset folder")
        print("   - Or use: from google.colab import files; files.upload()")
        print("\n2. Or mount Google Drive and place dataset there:")
        print("   - Uncomment the drive.mount() line at the top")
        print("   - Place dataset in your Drive")
        print("   - Update dataset_dir path above")
        return
    
    print("="*60)
    print("YOLO Training Script for Mussel Detection")
    print("="*60)
    
    # Step 1: Prepare dataset
    print("\n[Step 1] Converting Pascal VOC to YOLO format...")
    yaml_path = prepare_yolo_dataset(dataset_dir, yolo_dataset_dir)
    
    # Step 2: Train model
    print("\n[Step 2] Training YOLOv8n model...")
    
    # Detect device (Colab has CUDA)
    import torch
    if torch.cuda.is_available():
        device = 'cuda'
        print(f"✓ CUDA available! Using GPU: {torch.cuda.get_device_name(0)}")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'  # Apple Silicon
        print("✓ MPS available, using Apple Silicon GPU")
    else:
        device = 'cpu'
        print("⚠ Using CPU (training will be slow)")
    
    # Use larger batch size for Colab GPU
    batch_size = 32 if device == 'cuda' else (8 if device == 'cpu' else 16)
    
    best_model = train_yolo_model(
        yaml_path,
        epochs=50,
        imgsz=416,
        batch=batch_size,
        device=device
    )
    
    print(f"\n✓ Training complete! Best model: {best_model}")
    
    # In Colab, provide download instructions
    if IN_COLAB:
        print("\n" + "="*60)
        print("To download your trained model:")
        print("="*60)
        print("Run this in a new cell:")
        print(f"  from google.colab import files")
        print(f"  files.download('{best_model}')")
        print("="*60)


if __name__ == "__main__":
    main()

