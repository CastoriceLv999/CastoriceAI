import multiprocessing
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    multiprocessing.freeze_support()
    import uvicorn
    from fastapi.staticfiles import StaticFiles
    from main import app
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, 'path', None) != '/']
    app.mount('/', StaticFiles(directory=os.environ['CASTORICE_WEB_DIR'], html=True), name='desktop')
    uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]), log_level='warning')
