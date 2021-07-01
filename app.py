import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from flask_paginate import Pagination, get_page_args
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

# --- Config
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

# --- Pagination

PER_PAGE = 8


# Pagination guides taken from
# https://gist.github.com/mozillazg/69fb40067ae6d80386e10e105e6803c9
def paginated(recipes):
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')
    offset = page * PER_PAGE - PER_PAGE
    return recipes[offset: offset + PER_PAGE]


def pagination_args(recipes):
    page, per_page, offset = get_page_args(
                            page_parameter='page',
                            per_page_parameter='per_page')
    total = len(recipes)
    return Pagination(page=page, per_page=PER_PAGE, total=total)


# --- Homepage
@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    recipes = list(mongo.db.recipes.find().sort("recipe_name", 1))
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    recipes_paginated = paginated(recipes)
    pagination = pagination_args(recipes)
    return render_template("recipes.html", recipes=recipes_paginated,
                           categories=categories, pagination=pagination)


# --- Search
@app.route("/search", methods=["GET"])
def search():
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')
    query = request.args.get('query')

    recipes = list(mongo.db.recipes.find(
        {"$text": {"$search": str(query)}}))
    categories = mongo.db.categories.find()
    recipes_paginated = paginated(recipes)
    pagination = pagination_args(recipes)
    flash(query)
    flash(page)
    return render_template("recipes.html", recipes=recipes_paginated,
                           categories=categories,
                           pagination=pagination)


# --- Categories
@app.route("/category_search/<category_name>")
def category_search(category_name):
    recipes = list(mongo.db.recipes.find(
        {"$text": {"$search": category_name}}))
    recipes_paginated = paginated(recipes)
    pagination = pagination_args(recipes)
    categories = list(mongo.db.categories.find())
    return render_template(
        "recipes.html", recipes=recipes_paginated, categories=categories,
        pagination=pagination)


# --- Register new user
@app.route("/register", methods=["GET", "POST"])
def register():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
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
        return redirect(url_for("my_recipes", username=session["user"]))
    return render_template("register.html", categories=categories)


# --- Log in
@app.route("/login", methods=["GET", "POST"])
def login():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # check password
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("username").lower()
                        flash("Welcome, {}".format(
                            request.form.get("username").capitalize()))
                        return redirect(url_for(
                            "my_recipes", username=session["user"],
                            categories=categories))
            else:
                # invalid password
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))
        else:
            # username incorrect
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html", categories=categories)


# --- User's recipes
@app.route("/my_recipes/<username>")
def my_recipes(username):
    # grabe the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    recipes = list(mongo.db.recipes.find({'added_by': username}))
    recipes_paginated = paginated(recipes)
    pagination = pagination_args(recipes)
    categories = list(mongo.db.categories.find().sort("category_name", 1))

    if session["user"]:
        return render_template(
            "my_recipes.html", username=username, recipes=recipes_paginated,
            categories=categories, pagination=pagination)

    return redirect(url_for("login"))


# --- Log out
@app.route("/logout")
def logout():
    # remove user from session cookies
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


# --- Add Recipe
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


# --- Recipes
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
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        recipes = list(mongo.db.recipes.find({'added_by': username}))
        recipes_paginated = paginated(recipes)
        pagination = pagination_args(recipes)
        categories = list(mongo.db.categories.find().sort("category_name", 1))
        return render_template(
            "my_recipes.html", recipes=recipes_paginated,
            username=username, categories=categories, pagination=pagination)

    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    recipe = mongo.db.recipes.find_one({'_id': ObjectId(recipe_id)})
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template(
                "edit_recipe.html", recipe=recipe,
                username=username, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


# --- Manage Categories
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


# --- Error handlers from https://www.askpython.com/
#  Handling error 404 and displaying relevant web page
@app.errorhandler(404)
def function_name(error):
    return render_template('404.html'), 404


# Handling error 500 and displaying relevant web page
@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


# Handling error 403 and displaying relevant web page
@app.errorhandler(403)
def internal_error(error):
    return render_template('403.html'), 403

# --- Run the app
if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
