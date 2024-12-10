### INF601 - Advanced Programming in Python
### Mackenzie Freeman
### Final Project


# Final Project - Company Handbook

## Description

A handbook web app allowing users to view and request clarifications on company policies.

## Getting Started

### Dependencies
Navigate to the mysite directory:
```
cd mysite
```

You can install all required libraries using the following command:
```
pip install -r requirements.txt
```

### Setup Database

After installing dependencies, create the database schema using:
```
python manage.py makemigrations
```

Then apply the migrations:
```
python manage.py migrate
```

### Admin Setup

Create an administrator account for accessing the /admin dashboard:
```
python manage.py createsuperuser
```

### Running the Application

To start the application and run it locally, use the command:
```
python manage.py runserver
```
Access the application at:
* Handbook: Visit http://127.0.0.1:8000/handbook in your web browser.
* Admin: Visit http://127.0.0.1:8000/admin in your web browser.

## Features

### User Features
* Home Page: Welcomes users and introduces the handbook.
* Policy Section List Page: Displays a list of all policy sections.
* Section Page: Shows detailed policies for the selected section.
* Request Form Page: Allows users to submit questions or requests for clarification on policies.
* Login/Register Pages: Allows user to login or create an account to view handbook.

### Admin Features
* Policy Management: Add, edit, and manage policies.
* Policy Request Management: Track and resolve user-submitted requests.
* Section Management: Define and manage policy sections.

## Help

Common issues and troubleshooting:
* Database Migrations: Ensure the database server is running if migrations fail, then retry makemigrations and migrate.

## Authors

Mackenzie Freeman
[LinkedIn](https://www.linkedin.com/in/mackenzie-lyn-freeman/)

## Acknowledgments

Inspiration, code snippets, etc.
* [Django Tutorial](https://docs.djangoproject.com/en/4.2/intro/tutorial01/)
* [Django Docs](https://docs.djangoproject.com/en/5.1/)
* [Django Admin](https://docs.djangoproject.com/en/5.1/ref/contrib/admin/)
* [ChatGPT](https://chatgpt.com/share/672e6f74-59dc-800b-b531-281963cffbb1)
* [BootStrap Docs](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
* [LearnDjango](https://learndjango.com/tutorials/django-login-and-logout-tutorial)
* [Django-Anymail](https://github.com/anymail/django-anymail)
* [Stack Overflow - Dharanidhar Reddy](https://stackoverflow.com/a/71084228)
* [sitepoint](https://www.sitepoint.com/style-html-details-element/)
