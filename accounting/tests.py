#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from utils import PolicyAccounting


"""
#######################################################
Test Suite for Accounting
#######################################################
"""

class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()


    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)

        # Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()


    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)  # 300

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        import logging
        logging.info("Invoice.bill_date")
        logging.info(pa.return_account_balance(date_cursor=invoices[3].bill_date))

        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)



class TestReturnAccountBalanceMonthly(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()


    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_monthly_on_eff_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)

        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 100)

    def test_monthly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[11].bill_date), 1200)

    def test_monthly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=200))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)


class TestEvaluateCancellationPendingDueToNonPay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 2, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        cls.policy.billing_schedule = "Quarterly"
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_pending_cancellation_true(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date_cursor=date(2015, 3, 8)), True)

    def test_pending_cancellation_false(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date_cursor=date(2015, 2, 8)), False)

    def test_pending_cancellation_equal_due_date_true(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date_cursor=date(2015, 3, 1)), True)


class TestEvaluateCancelNoDescription(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 2, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        cls.policy.billing_schedule = "Quarterly"
        db.session.add(cls.policy)
        db.session.commit()

        cls.payments = Payment(cls.policy.id, cls.test_insured.id, 300, date(2015, 2, 1))
        db.session.add(cls.payments)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.delete(cls.payments)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_policy_cancelled_without_description(self):
        pa = PolicyAccounting(self.policy.id)
        pa.evaluate_cancel(date(2015, 5, 5), '')

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date) \
            .all()

        self.assertEquals(invoices[0].deleted, False)
        self.assertEquals(invoices[1].deleted, True)
        self.assertEquals(invoices[2].deleted, True)
        self.assertEquals(invoices[3].deleted, True)

        self.assertEquals(self.policy.cancel_date, datetime.now().date())
        self.assertEquals(self.policy.cancel_description, None)


class TestEvaluateCancelWithDescription(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 2, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        cls.policy.billing_schedule = "Quarterly"
        db.session.add(cls.policy)
        db.session.commit()

        cls.payments = Payment(cls.policy.id, cls.test_insured.id, 300, date(2015, 2, 1))
        db.session.add(cls.payments)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.delete(cls.payments)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_policy_cancelled_with_description(self):
        self.policy.cancel_date = None
        self.policy.cancel_description = None

        pa = PolicyAccounting(self.policy.id)

        reset_invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
            .order_by(Invoice.bill_date) \
            .all()
        for reset_invoice in reset_invoices:
            reset_invoice.deleted = False
        db.session.commit()

        pa.evaluate_cancel(date(2015, 5, 5), 'Just Because')

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date)\
            .all()

        self.assertEquals(invoices[0].deleted, False)
        self.assertEquals(invoices[1].deleted, True)
        self.assertEquals(invoices[2].deleted, True)
        self.assertEquals(invoices[3].deleted, True)

        self.assertEquals(self.policy.cancel_date, datetime.now().date())
        self.assertEquals(self.policy.cancel_description, 'Just Because')
