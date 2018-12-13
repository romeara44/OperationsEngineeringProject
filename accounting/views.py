# You will probably need more methods from flask but this one is a good start.
# from flask import render_template
from flask import Flask, url_for, request, render_template;

# Import things from Flask that we need.
from accounting import app, db
from utils import PolicyAccounting

# Import our models
from models import Contact, Invoice, Policy

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')


@app.route("/invoices", methods=['POST', 'GET'])
def main_page():
    if request.method == 'GET':
        # send the user the form
        return render_template('invoices.html')
    elif request.method == 'POST':
        # read form data
        policy_number = request.form['policy_number']
        effective_date = request.form['effective_date']

    # Use Policy Number to get Policy Id
    policy = Policy.query.filter_by(policy_number=policy_number)\
        .first()

    # Pass Policy ID to the filter mechnism
    invoices = Invoice.query.filter_by(policy_id=policy.id)\
        .order_by(Invoice.bill_date)\
        .all()

    # pa = PolicyAccounting(policy.id)
    pa = PolicyAccounting(2)

    balance = pa.return_account_balance(effective_date)

    return render_template("invoices.html", invoices=invoices, balance=balance)
