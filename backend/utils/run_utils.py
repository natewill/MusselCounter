import aiosqlite
from datetime import datetime
from pathlib import Path
import json
import os
from utils.model_utils import load_model, run_inference_on_image


async def create_run(
    db: aiosqlite.Connection,
    batch_id: int,
    model_id: int,
    threshold: float = 0.5
) -> int:
    """
    Create a new run record in the database.
    
    Args:
        db: Database connection
        batch_id: Batch ID to run inference on
        model_id: Model ID to use for inference
        threshold: Threshold score for classification (default 0.5)
        
    Returns:
        Run ID of the created run
    """
    now = datetime.now().isoformat()
    
    cursor = await db.execute(
        """INSERT INTO run (batch_id, model_id, started_at, status, threshold)
           VALUES (?, ?, ?, ?, ?)""",
        (batch_id, model_id, now, 'pending', threshold)
    )
    run_id = cursor.lastrowid
    await db.commit()
    
    return run_id


async def get_run(db: aiosqlite.Connection, run_id: int):
    """
    Get run record from database.
    
    Args:
        db: Database connection
        run_id: Run ID
        
    Returns:
        Row with run data, or None if not found
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE run_id = ?",
        (run_id,)
    )
    return await cursor.fetchone()


async def update_run_status(
    db: aiosqlite.Connection,
    run_id: int,
    status: str,
    error_msg: str = None
):
    """
    Update run status and optionally error message.
    
    Args:
        db: Database connection
        run_id: Run ID
        status: New status ('pending', 'running', 'completed', 'failed')
        error_msg: Optional error message
    """
    updates = ["status = ?"]
    values = [status]
    
    if error_msg is not None:
        updates.append("error_msg = ?")
        values.append(error_msg)
    
    # Set finished_at if status is completed or failed
    if status in ('completed', 'failed'):
        updates.append("finished_at = ?")
        values.append(datetime.now().isoformat())
    
    values.append(run_id)
    
    await db.execute(
        f"UPDATE run SET {', '.join(updates)} WHERE run_id = ?",
        values
    )
    await db.commit()


async def process_image_for_run(
    db: aiosqlite.Connection,
    run_id: int,
    image_id: int,
    model_device,
    threshold: float,
    model_type: str
) -> bool:
    """
    Process a single image for a run.
    
    Args:
        db: Database connection
        run_id: Run ID
        image_id: Image ID to process
        threshold: Threshold score for classification
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get image from database
        cursor = await db.execute(
            "SELECT stored_path FROM image WHERE image_id = ?",
            (image_id,)
        )
        image_row = await cursor.fetchone()
        
        if not image_row:
            await db.execute(
                "UPDATE image SET error_msg = ? WHERE image_id = ?",
                (f"Image not found in database", image_id)
            )
            await db.commit()
            return False
        
        image_path = image_row['stored_path']
        
        # Check if file exists
        if not Path(image_path).exists():
            await db.execute(
                "UPDATE image SET error_msg = ? WHERE image_id = ?",
                (f"Image file not found: {image_path}", image_id)
            )
            await db.commit()
            return False
        
        # Run inference
        try:
            result = run_inference_on_image(model_device, image_path, threshold, model_type)
            
            # Print full inference results
            print(f"  Inference Results:")
            print(f"    Live Count: {result['live_count']}")
            print(f"    Dead Count: {result['dead_count']}")
            print(f"    Image Dimensions: {result['image_width']}x{result['image_height']}")
            print(f"    Total Polygons Detected: {len(result['polygons'])}")
            
            if result['polygons']:
                print(f"    Polygon Details:")
                for i, polygon in enumerate(result['polygons'], 1):
                    print(f"      Polygon {i}:")
                    print(f"        Class: {polygon['class']}")
                    print(f"        Confidence: {polygon['confidence']:.4f}")
                    print(f"        Bounding Box: {polygon['bbox']}")
                    print(f"        Coordinates: {polygon['coords']}")
            else:
                print(f"    No polygons detected (below threshold or no detections)")
            
        except Exception as e:
            print(f"  ERROR during inference: {str(e)}")
            await db.execute(
                "UPDATE image SET error_msg = ? WHERE image_id = ?",
                (f"Inference error: {str(e)}", image_id)
            )
            await db.commit()
            return False
        
        # Save polygon data to file
        polygon_path = None
        if result['polygons']:
            polygon_dir = Path("data/polygons")
            polygon_dir.mkdir(parents=True, exist_ok=True)
            
            polygon_path = polygon_dir / f"{image_id}.json"
            with open(polygon_path, 'w') as f:
                json.dump({
                    'polygons': result['polygons'],
                    'live_count': result['live_count'],
                    'dead_count': result['dead_count'],
                    'threshold': threshold
                }, f, indent=2)
            polygon_path = str(polygon_path)
        
        # Update image in database
        now = datetime.now().isoformat()
        await db.execute(
            """UPDATE image 
               SET live_mussel_count = ?, 
                   dead_mussel_count = ?,
                   stored_polygon_path = ?,
                   updated_at = ?,
                   error_msg = NULL
               WHERE image_id = ?""",
            (
                result['live_count'],
                result['dead_count'],
                polygon_path,
                now,
                image_id
            )
        )
        await db.commit()
        
        return True
        
    except Exception as e:
        # Update image with error
        try:
            await db.execute(
                "UPDATE image SET error_msg = ? WHERE image_id = ?",
                (f"Processing error: {str(e)}", image_id)
            )
            await db.commit()
        except:
            pass
        return False


async def process_batch_run(db: aiosqlite.Connection, run_id: int):
    """
    Main orchestration function to process all images in a batch run.
    
    Args:
        db: Database connection
        run_id: Run ID to process
    """
    try:
        # Get run details
        run = await get_run(db, run_id)
        if not run:
            return
        
        batch_id = run['batch_id']
        model_id = run['model_id']
        threshold = run['threshold']
        started_at = run['started_at']
        
        # Print run start information
        print("\n" + "="*80)
        print("RUN STARTED")
        print("="*80)
        print(f"Run ID: {run_id}")
        print(f"Batch ID: {batch_id}")
        print(f"Model ID: {model_id}")
        print(f"Threshold: {threshold}")
        print(f"Started At: {started_at}")
        print("-"*80)
        
        # Update status to running
        await update_run_status(db, run_id, 'running')
        
        # Get model from database
        from utils.model_utils import get_model
        model_row = await get_model(db, model_id)
        if not model_row:
            await update_run_status(
                db, run_id, 'failed',
                f"Model {model_id} not found in database"
            )
            return
        
        weights_path = model_row['weights_path']
        model_type = model_row['type']
        model_name = model_row['name']
        
        print(f"Model Name: {model_name}")
        print(f"Model Type: {model_type}")
        print(f"Model Weights Path: {weights_path}")
        print("-"*80)
        
        # Check if model file exists
        if not Path(weights_path).exists():
            print(f"ERROR: Model weights file not found: {weights_path}")
            await update_run_status(
                db, run_id, 'failed',
                f"Model weights file not found: {weights_path}"
            )
            return
        
        # Load model (returns tuple of model and device)
        print("Loading model...")
        try:
            model_device = load_model(weights_path, model_type)
            print("Model loaded successfully")
        except Exception as e:
            print(f"ERROR: Failed to load model: {str(e)}")
            await update_run_status(
                db, run_id, 'failed',
                f"Failed to load model: {str(e)}"
            )
            return
        
        # Get all images in the batch
        from utils.batch_utils import get_batch_images
        images = await get_batch_images(db, batch_id)
        
        if not images:
            print("ERROR: No images found in batch")
            await update_run_status(
                db, run_id, 'failed',
                "No images found in batch"
            )
            return
        
        print(f"Total images to process: {len(images)}")
        print("="*80 + "\n")
        
        # Process each image
        total_images = 0
        total_live_count = 0
        total_dead_count = 0
        successful_images = 0
        failed_images = []
        
        for idx, image in enumerate(images, 1):
            image_id = image['image_id']
            image_filename = image['filename'] if 'filename' in image.keys() else 'unknown'
            image_path = image['stored_path'] if 'stored_path' in image.keys() else 'unknown'
            
            print(f"\n[{idx}/{len(images)}] Processing Image ID: {image_id}")
            print(f"  Filename: {image_filename}")
            print(f"  Path: {image_path}")
            
            success = await process_image_for_run(
                db, run_id, image_id, model_device, threshold, model_type
            )
            
            if success:
                successful_images += 1
                # Get updated counts from image
                cursor = await db.execute(
                    "SELECT live_mussel_count, dead_mussel_count FROM image WHERE image_id = ?",
                    (image_id,)
                )
                img_row = await cursor.fetchone()
                if img_row:
                    img_live = img_row['live_mussel_count'] or 0
                    img_dead = img_row['dead_mussel_count'] or 0
                    total_live_count += img_live
                    total_dead_count += img_dead
                    print(f"  ✓ Success - Live: {img_live}, Dead: {img_dead}")
                else:
                    print(f"  ✓ Success - Counts not available")
            else:
                failed_images.append(image_id)
                # Get error message if available
                cursor = await db.execute(
                    "SELECT error_msg FROM image WHERE image_id = ?",
                    (image_id,)
                )
                error_row = await cursor.fetchone()
                error_msg = error_row['error_msg'] if error_row and error_row['error_msg'] else "Unknown error"
                print(f"  ✗ Failed - {error_msg}")
            
            total_images += 1
        
        # Update run with results
        now = datetime.now().isoformat()
        final_status = 'completed' if successful_images == total_images else 'completed_with_errors'
        
        await db.execute(
            """UPDATE run 
               SET total_images = ?,
                   live_mussel_count = ?,
                   status = ?,
                   finished_at = ?
               WHERE run_id = ?""",
            (total_images, total_live_count, final_status, now, run_id)
        )
        
        # Update batch live_mussel_count from run's count
        await db.execute(
            "UPDATE batch SET live_mussel_count = ? WHERE batch_id = ?",
            (total_live_count, batch_id)
        )
        
        await db.commit()
        
        # Print run completion summary
        print("\n" + "="*80)
        print("RUN COMPLETED")
        print("="*80)
        print(f"Run ID: {run_id}")
        print(f"Status: {final_status}")
        print(f"Finished At: {now}")
        print("-"*80)
        print(f"Total Images Processed: {total_images}")
        print(f"Successful Images: {successful_images}")
        print(f"Failed Images: {len(failed_images)}")
        if failed_images:
            print(f"Failed Image IDs: {failed_images}")
        print("-"*80)
        print(f"Total Live Mussel Count: {total_live_count}")
        print(f"Total Dead Mussel Count: {total_dead_count}")
        print("="*80 + "\n")
        
    except Exception as e:
        # Set run status to failed
        print("\n" + "="*80)
        print("RUN FAILED")
        print("="*80)
        print(f"Run ID: {run_id}")
        print(f"Error: {str(e)}")
        print("="*80 + "\n")
        try:
            await update_run_status(
                db, run_id, 'failed',
                f"Run processing error: {str(e)}"
            )
        except:
            pass

