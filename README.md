# Important Links

A premium light-mode website manager built using Python Flask, HTML,
CSS, JavaScript and SQLite3.

## Project structure

important_links/
├── app.py
├── requirements.txt
├── run.sh
├── README.md
├── instance/
│   ├── important_links.db
│   └── secret_key.txt
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── dashboard.html
│   ├── link_form.html
│   ├── settings.html
│   └── error.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js

## Installation

1. Install Python in Termux:
   pkg install python

2. Enter the project directory:
   cd important_links

3. Start the application:
   bash run.sh

4. Open:
   http://127.0.0.1:5000

## Default admin credentials

Username: admin
Password: 12345

Change these credentials from Admin Login > Settings.

## Database

SQLite database:
instance/important_links.db

Do not delete the instance directory if you want to preserve your
website links, administrator account and session secret.

## Sorting

Log in and long-press the drag handle (⠿), then drag a website
to its new position. The order is saved in SQLite.

## External dependency

SortableJS is loaded from jsDelivr for touch-friendly drag sorting.
An internet connection is needed for this library to load.
