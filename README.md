# KASHF – كاشف

تشغيل سريع:

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

افتح: http://localhost:8000

للنشر على Render:
- Build: pip install -r requirements.txt
- Start: uvicorn app:app --host 0.0.0.0 --port $PORT
