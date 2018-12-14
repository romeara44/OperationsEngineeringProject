#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

import logging
"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""


class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        # If no invoices exist for current policy_id, call make_invoice
        if not self.policy.invoices:
            self.make_invoices()
            # self.make_invoices(policy_id, self.policy.effective_date, self.policy.annual_premium)

    def return_account_balance(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date >= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date >= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """

        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.due_date <= date_cursor, date_cursor < Invoice.cancel_date)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                print "THIS POLICY STATUS IS PENDING CANCELED"
                return True
                break
        else:
            print "THIS POLICY IS NOT PENDING CANCELED"

        return False

    def evaluate_cancel(self, date_cursor=None, description=''):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                print "THIS POLICY SHOULD HAVE CANCELED"
                break
        else:
            print "THIS POLICY SHOULD NOT CANCEL"

        # Get all the payments for the policy cancelling
        payments = Payment.query.filter_by(policy_id=self.policy.id) \
            .all()

        # Get all invoices for the policy cancelling
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
            .order_by(Invoice.bill_date) \
            .all()

        # Set all invoices without corresponding payment, to deleted
        for i in range(len(payments), len(invoices)):
            invoices[i].deleted = True

        self.policy.cancel_date = datetime.now().date()

        if description:
            self.policy.cancel_description = description

        db.session.commit()


    def make_invoices(self):
        for invoice in self.policy.invoices:
            invoice.delete()

        billing_schedules = {'Annual': None, 'Two-Pay': 3, 'Quarterly': 4, 'Monthly': 12}

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date,  # bill_date
                                self.policy.effective_date + relativedelta(months=1),  # due
                                self.policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            pass
        elif self.policy.billing_schedule == "Two-Pay":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i * 6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Quarterly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i * 3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Monthly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i * 1
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

    def change_billing_schedule(self, date_cursor=None, billing_schedule=''):
        if billing_schedule == '':
            return

        if not date_cursor:
            date_cursor = datetime.now().date()

        # set the billing schedule
        self.policy.billing_schedule = billing_schedule

        # Get all the payments
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
            .all()

        payment_amount = 0
        for payment in payments:
            payment_amount += payment.amount_paid

        payment_date = payments[len(payments) - 1].transaction_date

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date)\
            .all()

        invoice_amount = 0

        for i in range(len(payments), len(invoices)):
            invoices[i].deleted = True
            invoice_amount += invoices[i].amount_due

        self.make_invoices_remainder(payment_date, invoice_amount)

        db.session.commit()

    def make_invoices_remainder(self, date_cursor=None, amount=0):
        if not date_cursor:
            date_cursor = datetime.now().date()
        from dateutil import rrule
        from datetime import date

        month_list = list(rrule.rrule(rrule.MONTHLY, dtstart=date_cursor, until=date(date_cursor.year, 12, 31)))

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                date_cursor,  # bill_date
                                date_cursor + relativedelta(months=1),  # due_date
                                date_cursor + relativedelta(months=1, days=14),  # cancel_date
                                amount)
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            first_invoice.amount_due = amount
        elif self.policy.billing_schedule == "Two-Pay":
            first_invoice.amount_due = amount
        elif self.policy.billing_schedule == "Quarterly":
            quarters_left = 0
            months_in_quarter = 0

            if len(month_list) == 12:
                quarters_left = 4
                months_in_quarter = 3
            elif len(month_list) >= 10:
                quarters_left = 3
                months_in_quarter = len(month_list) / quarters_left
            elif len(month_list) >= 7:
                quarters_left = 2
                months_in_quarter = len(month_list) / quarters_left
            else:
                quarters_left = 1
                months_in_quarter = 1

            first_invoice.amount_due = first_invoice.amount_due / quarters_left
            for i in range(1, len(month_list)):
                months_after_eff_date = i * months_in_quarter
                bill_date = date_cursor + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  amount / len(month_list))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Monthly":
            first_invoice.amount_due = first_invoice.amount_due / len(month_list)
            for i in range(1, len(month_list)):
                months_after_eff_date = i * 1
                bill_date = date_cursor + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  amount / len(month_list))
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()


################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    # 5. Policy Four
    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()
