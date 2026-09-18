from PIL import Image
import io

def compress_image(file, max_width=2000, quality=100):  
    try:
        file.seek(0)  
        img = Image.open(file)
        file.seek(0)  
        original_format = img.format.lower() if img.format else 'jpeg'

        if original_format in ['jpg', 'jpeg'] and img.width <= max_width:
            file.seek(0)  
            #logging.info("Skipping compression for JPEG (no resize needed)")
            return file

        resized = False
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
            resized = True
        
        output = io.BytesIO()
        
        if original_format in ['jpg', 'jpeg']:
            img.save(output, format='JPEG', quality=quality, optimize=True)
        elif original_format == 'png':
            img.save(output, format='PNG', optimize=True, compress_level=5)  
        else:

            img.save(output, format='PNG', optimize=True, compress_level=5)
        
        output.seek(0)
        return output
    except Exception as e:
        #logging.error(f"Image compression failed: {e}")
        file.seek(0)  
        return file  
