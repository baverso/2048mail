import uvicorn
from devserver.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "devserver.core.application:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL,
        access_log=settings.ACCESS_LOG
    ) 