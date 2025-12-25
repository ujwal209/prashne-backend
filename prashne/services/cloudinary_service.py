import cloudinary
import cloudinary.uploader
from prashne.core.config import settings

# Configure Cloudinary
cloudinary.config( 
  cloud_name = settings.CLOUDINARY_CLOUD_NAME, 
  api_key = settings.CLOUDINARY_API_KEY, 
  api_secret = settings.CLOUDINARY_API_SECRET 
)

def upload_file_to_cloudinary(file_content: bytes, filename: str) -> str:
    """
    Uploads bytes to Cloudinary and returns the secure URL.
    """
    try:
        # Uploading byte stream directly. 
        # resource_type="auto" allows pdfs/images
        response = cloudinary.uploader.upload(
            file_content, 
            public_id=filename.split('.')[0], # Use filename without extension as ID
            folder="resumes",
            resource_type="auto"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary Upload Error: {str(e)}")
        raise e
