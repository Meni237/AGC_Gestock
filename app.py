from fastapi import FastAPI, Request, Form, Depends, RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, database, auth

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user and auth.verify_password(password, user.hashed_password):
        return RedirectResponse(url="/dashboard", status_code=303)
    return HTMLResponse("<h1 style='color: red; text-align: center; margin-top: 50px;'>Identifiants incorrects. <a href='/'>Réessayer</a></h1>", status_code=400)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(database.get_db)):
    total_items = db.query(models.Item).count()
    low_stock = db.query(models.Item).filter(models.Item.quantity <= models.Item.min_quantity).count()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"total_items": total_items, "low_stock": low_stock})

@app.get("/items", response_class=HTMLResponse)
def get_items(request: Request, db: Session = Depends(database.get_db)):
    items = db.query(models.Item).all()
    return templates.TemplateResponse(request=request, name="items.html", context={"items": items})

@app.post("/items/add")
def add_item(name: str = Form(...), category: str = Form(...), quantity: int = Form(...), min_quantity: int = Form(...), db: Session = Depends(database.get_db)):
    new_item = models.Item(name=name, category=category, quantity=quantity, min_quantity=min_quantity)
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/items", status_code=303)