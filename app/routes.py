from flask import Blueprint, render_template

main = Blueprint("main", __name__)

@main.get("/")
def dashboard():
    return render_template("dashboard.html")

@main.get("/shipments")
def shipments():
    return render_template("shipments.html")

@main.get("/operations")
def operations():
    return render_template("operations.html")
