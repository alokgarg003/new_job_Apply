#!/usr/bin/env python3
# run_server.py
"""
Start the JobSpy API server.
"""
import uvicorn
from jobspy.config import get_config

if __name__ == "__main__":
    config = get_config()

    uvicorn.run(
        "jobspy.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
