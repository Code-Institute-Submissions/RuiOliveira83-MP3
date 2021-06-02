import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    recipes = list(mongo.db.recipes.find())
    categories = mongo.db.categories.find()
    return render_template(
        "recipes.html", recipes=recipes, categories=categories)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    categories = mongo.db.categories.find()
    return render_template(
        "recipes.html", recipes=recipes, categories=categories)


@app.route("/category_search/<category_name>")
def category_search(category_name):
    recipes = list(mongo.db.recipes.find(
        {"$text": {"$search": category_name}}))
    categories = list(mongo.db.categories.find())
    return render_template(
        "recipes.html", recipes=recipes, categories=categories)


@app.route("/register", methods=["GET", "POST"])
def register():
    categories = mongo.db.categories.find()
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for('register'))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("myrecipes", username=session["user"]))
    return render_template("register.html", categories=categories)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        #check if username exists in db
        existing_user =mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # check password
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    # valid password
                    session["user"] = request.form.get("username").lower()
                    flash("Welcome, {}".format(
                        request.form.get("username").capitalize()))
                    return redirect(url_for(
                        "myrecipes", username=session["user"]))
            else:
                # invalid password
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username incorrect
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/myrecipes/<username>", methods=["GET", "POST"])
def myrecipes(username):
    # grabe the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    recipes = list(mongo.db.recipes.find())
    categories = mongo.db.categories.find()
    if session["user"]:
        return render_template("myrecipes.html", username=username, recipes=recipes, categories=categories)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    #remove user from session cookies
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        recipe = {
            "category_name": request.form.getlist("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "ingredients": request.form.get("ingredients"),
            "method": request.form.get("method"),
            "recipe_img": request.form.get("recipe_img"),
            "added_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("add_recipe.html", categories=categories)

@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    recipe = mongo.db.recipes.find_one({'_id': ObjectId(recipe_id)})
    return render_template("recipe.html", recipe=recipe, categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        submit = {
            "category_name": request.form.getlist("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "ingredients": request.form.get("ingredients"),
            "method": request.form.get("method"),
            "recipe_img": request.form.get("recipe_img"),
            "added_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Successfully Updated")

    recipe = mongo.db.recipes.find_one({'_id': ObjectId(recipe_id)})
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template(
        "edit_recipe.html", recipe=recipe, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


@app.route("/get_categories", methods=["GET", "POST"])
def get_categories():
    if request.method == "POST":
        category_added = {
            "category_name": request.form.get("category_name"),
        }
        mongo.db.categories.insert_one(category_added)
        flash("Category Successfully Added")
        return redirect(url_for("get_categories"))

    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully Deleted")
    return redirect(url_for("get_categories"))



if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True)
        