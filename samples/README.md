# Sample Images

Place the company's provided vehicle sample images in this directory.

Do not invent or commit fake sample results. After the real images are available, run:

```bash
curl -X POST -F "image=@samples/<filename>" http://localhost:8000/api/v1/images
```

Then poll status and fetch results using the returned `processing_id`.
