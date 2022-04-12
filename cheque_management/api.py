# -*- coding: utf-8 -*-
# Copyright (c) 2017, Direction and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt, cstr, nowdate, comma_and
from frappe import throw, msgprint, _

def pe_before_submit(self, method):
	if self.mode_of_payment == "Cheque" and self.payment_type == "Receive":
		notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not notes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		
		self.db_set("cheque_paid_to", self.paid_to)	
		self.db_set("paid_to", notes_acc)
	if self.mode_of_payment == "Cheque" and self.payment_type == "Pay":
		notes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
		if not notes_acc:
			frappe.throw(_("Payable Notes Account not defined in the company setup page"))
		self.db_set("cheque_paid_from", self.paid_from)		
		self.db_set("paid_from", notes_acc)

def pe_on_submit(self, method):
	hh_currency = erpnext.get_company_currency(self.company)
	if self.mode_of_payment == "Cheque" and self.paid_from_account_currency != hh_currency:
		frappe.throw(_("You cannot use foreign currencies with Mode of Payment   Cheque"))
	if self.mode_of_payment == "Cheque" and self.paid_to_account_currency != hh_currency:
		frappe.throw(_("You cannot use foreign currencies with Mode of Payment   Cheque"))
	if self.mode_of_payment == "Cheque" and self.payment_type == "Receive":
		notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not notes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		self.db_set("paid_to", notes_acc)
		crs_acc = frappe.db.get_value("Company", self.company, "cross_transaction_account")
		if not crs_acc:
			frappe.throw(_("Cross Transaction Account not defined in the company setup page"))

		journal = make_journal_entry(self, self.paid_from, crs_acc, self.base_received_amount, self.posting_date)
		rc = frappe.new_doc("Receivable Cheques")
		rc.cheque_no = self.reference_no 
		rc.cheque_date = self.reference_date 
		rc.customer = self.party
		rc.company = self.company
		rc.payment_entry = self.name
		if self.project:
			rc.project = self.project
		rc.currency = hh_currency
		rc.amount = self.base_received_amount
		rc.exchange_rate = 1
		rc.remarks = self.remarks
		rc.reference_journal = journal.name
		rc.docstatus=1
		rc.deposit_bank=self.cheque_paid_to # add by jk
		rc.cheque_status = 'Cheque Received'
		rc.set("status_history", [
			{
				"status": "Cheque Received",
				"transaction_date": nowdate(),
				"credit_account": self.paid_from,
				"debit_account": notes_acc
			}
		])
		rc.insert(ignore_permissions=True)
		rc.submit()
		message = """<a href="#Form/Receivable Cheques/%s" target="_blank">%s</a>""" % (rc.name, rc.name)
		msgprint(_("Receivable Cheque {0} created").format(comma_and(message)))

	if self.mode_of_payment == "Cheque" and self.payment_type == "Pay":
		notes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
		if not notes_acc:
			frappe.throw(_("Payable Notes Account not defined in the company setup page"))
		self.db_set("paid_from", notes_acc)
		rec_acc = frappe.db.get_value("Company", self.company, "default_payable_account")
		if not rec_acc:
			frappe.throw(_("Default Payable Account not defined in the company setup page"))
		pc = frappe.new_doc("Payable Cheques")
		pc.cheque_no = self.reference_no 
		pc.cheque_date = self.reference_date 
		pc.party_type = self.party_type
		pc.party = self.party
		pc.company = self.company
		pc.payment_entry = self.name
		if self.project:
			pc.project = self.project
		pc.currency = hh_currency
		pc.amount = self.base_paid_amount
		pc.exchange_rate = 1
		pc.remarks = self.remarks  
		pc.bank=self.cheque_paid_from # add by jk
		#pc.cheque_status = 'Cheque Received'
		pc.docstatus=1
		pc.set("status_history", [
			{
				"status": "Cheque Issued",
				"transaction_date": nowdate(),
				"credit_account": notes_acc,
				"debit_account": rec_acc
			}
		])
		pc.insert(ignore_permissions=True)
		pc.submit()
		message = """<a href="#Form/Payable Cheques/%s" target="_blank">%s</a>""" % (pc.name, pc.name)
		msgprint(_("Payable Cheque {0} created").format(comma_and(message)))

def pe_on_cancel(self, method):
	if frappe.db.sql("""select name from `tabReceivable Cheques` where payment_entry=%s and docstatus<>2  
				and not cheque_status in ("Cheque Cancelled","Cheque Rejected")""" , (self.name)):
		frappe.throw(_("Cannot Cancel this Payment Entry as it is Linked with Receivable Cheque"))
	if frappe.db.sql("""select name from `tabPayable Cheques` where payment_entry=%s and docstatus<>2  
				and cheque_status<>'Cheque Cancelled'""" , (self.name)):
		frappe.throw(_("Cannot Cancel this Payment Entry as it is Linked with Payable Cheque"))
	return

def make_journal_entry(self, account1, account2, amount, posting_date=None, party_type=None, party=None, cost_center=None):
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = posting_date or nowdate()
		jv.due_date = posting_date or nowdate()
		jv.company = self.company
		jv.cheque_no = self.reference_no
		jv.cheque_date = self.reference_date
		jv.user_remark = self.remarks
		jv.multi_currency = 0
		jv.set("accounts", [
			{
				"account": account1,
				"party_type": self.party_type,
				"party": self.party,
				"cost_center": None,
				"project": self.project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0
			}, {
				"account": account2,
				"party_type": None,
				"party": None,
				"cost_center": None,
				"project": self.project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0
			}
		])
		jv.insert(ignore_permissions=True)
		jv.submit()
		frappe.db.commit()
		return jv