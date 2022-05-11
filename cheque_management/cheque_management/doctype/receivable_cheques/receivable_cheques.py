# -*- coding: utf-8 -*-
# Copyright (c) 2017, Direction and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr, nowdate, comma_and
from frappe import msgprint, _
from frappe.model.document import Document
from erpnext.accounts.utils import get_account_currency
from erpnext.setup.utils import get_exchange_rate
@frappe.whitelist()
def say_hello():
	frappe.msgprint("Hello There")
class ReceivableCheques(Document):
	#def __init__(): #self is the current instance
        #	pass
	def say_hi(self):
		frappe.msgprint('Hi there!')
	def autoname(self):
		name2 = frappe.db.sql("""select left(replace(replace(replace(sysdate(6), ' ',''),'-',''),':',''),14)""")[0][0]

		if name2:
			ndx = "-" + name2
		else:
			ndx = "-"

		self.name = self.cheque_no + ndx

	def validate(self):
		self.cheque_status = self.get_status()
		#msgprint("validate")

	@frappe.whitelist()
	def on_update(self):
		notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not notes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		elif len(notes_acc) < 4:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))

		uc_acc = frappe.db.get_value("Company", self.company, "cheques_under_collection_account")
		if not uc_acc:
			frappe.throw(_("Cheques Under Collection Account not defined in the company setup page"))
		elif len(uc_acc) < 4:
			frappe.throw(_("Cheques Under Collection Account not defined in the company setup page"))

		ct_acc = frappe.db.get_value("Company", self.company, "cross_transaction_account")
		if not ct_acc:
			frappe.throw(_("Cross Transaction Account not defined in the company setup page"))
		elif len(ct_acc) < 4:
			frappe.throw(_("Cross Transaction Account not defined in the company setup page"))

		
		if self.payment_entry:
			rec_acc = frappe.db.get_value("Payment Entry", self.payment_entry, "paid_from")
			if self.cheque_status == "Cheque Deposited":
				self.make_journal_entry(uc_acc, notes_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
			if self.cheque_status == "Cheque Cancelled":
				self.cancel_payment_entry()
			if self.cheque_status == "Cheque Collected":
				party = frappe.db.get_value("Payment Entry", self.payment_entry, "party")
				party_type = frappe.db.get_value("Payment Entry", self.payment_entry, "party_type")
				self.make_journal_entry(ct_acc, uc_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
				self.make_journal_entry(self.deposit_bank, rec_acc, self.amount, self.posting_date, party_type, party, cost_center=None, 
						save=True, submit=True, last=True)
			if self.cheque_status == "Cheque Returned":
				self.make_journal_entry(notes_acc, uc_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
			if self.cheque_status == "Cheque Rejected":
				#msgprint("rejected")
				self.cancel_payment_entry()
		else:
			if self.cheque_status == "Cheque Deposited":
				self.make_journal_entry(uc_acc, notes_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
			if self.cheque_status == "Cheque Cancelled":
				self.cancel_payment_entry_jv()
			if self.cheque_status == "Cheque Collected":
				party = frappe.db.get_value("Payment Entry", self.payment_entry, "party")
				party_type = frappe.db.get_value("Payment Entry", self.payment_entry, "party_type")
				self.make_journal_entry(ct_acc, uc_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
				self.make_journal_entry_jv(self.deposit_bank, self.journal_entry, self.amount, self.posting_date, party_type, party, cost_center=None, 
						save=True, submit=True, last=True)
			if self.cheque_status == "Cheque Returned":
				self.make_journal_entry(notes_acc, uc_acc, self.amount, self.posting_date, party_type=None, party=None, cost_center=None, 
						save=True, submit=True, last=False)
			if self.cheque_status == "Cheque Rejected":
				#msgprint("rejected")
				self.cancel_payment_entry_jv()

	def on_submit(self):
		self.set_status()

	def set_status(self, cheque_status=None):
		'''Get and update cheque_status'''
		if not cheque_status:
			cheque_status = self.get_status()
		self.db_set("cheque_status", cheque_status)

	def get_status(self):
		'''Returns cheque_status based on whether it is draft, submitted, scrapped or depreciated'''
		cheque_status = self.cheque_status
		if self.docstatus == 0:
			cheque_status = "Draft"
		if self.docstatus == 1 and self.cheque_status == "Draft":
			cheque_status = "Cheque Received"
		if self.docstatus == 2:
			cheque_status = "Cancelled"

		return cheque_status

	def cancel_payment_entry(self):

		if self.reference_journal:
			frappe.get_doc("Journal Entry", self.reference_journal).cancel()

		if self.payment_entry: 
			frappe.get_doc("Payment Entry", self.payment_entry).cancel()

		
		self.append("status_history", {
								"status": self.cheque_status,
								"transaction_date": nowdate(),
								"bank": self.deposit_bank
							})
		self.bank_changed = 1
		self.submit()
		message = """<a href="#Form/Payment Entry/%s" target="_blank">%s</a>""" % (self.payment_entry, self.payment_entry)
		#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))
		message = _("Payment Entry {0} Cancelled").format(comma_and(message))

		return message
	def cancel_payment_entry_jv(self):
		if self.reference_journal:
			frappe.get_doc("Journal Entry", self.reference_journal).cancel()
		if self.journal_entry:
			frappe.get_doc("Journal Entry", self.journal_entry).cancel()

		self.append("status_history", {
								"status": self.cheque_status,
								"transaction_date": nowdate(),
								"bank": self.deposit_bank
							})
		self.bank_changed = 1
		self.submit()
		message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (self.reference_journal, self.reference_journal)
		#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))
		message = _("Payment Entry {0} Cancelled").format(comma_and(message))

		return message

	def make_journal_entry(self, account1, account2, amount, posting_date=None, party_type=None, party=None, cost_center=None, 
							save=True, submit=False, last=False):
		naming_series = frappe.db.get_value("Company", self.company, "journal_entry_naming_series")
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")	
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = posting_date or nowdate()
		jv.company = self.company
		jv.cheque_no = self.cheque_no
		jv.cheque_date = self.cheque_date
		if naming_series:
			jv.naming_series=naming_series
		jv.user_remark = self.remarks or "Cheque Transaction"
		jv.multi_currency = 0
		jv.set("accounts", [
			{
				"account": account1,
				"party_type": party_type if (self.cheque_status == "Cheque Cancelled" or self.cheque_status == "Cheque Rejected") else None,
				"party": party if self.cheque_status == "Cheque Cancelled" else None,
				"cost_center": cost_center,
				"project": self.project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0
			}, {
				"account": account2,
				"party_type": party_type if self.cheque_status == "Cheque Received" or self.cheque_status == "Cheque Collected" else None,
				"party": party if self.cheque_status == "Cheque Received" or self.cheque_status == "Cheque Collected" else None,
				"cost_center": cost_center,
				"project": self.project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				"reference_type": "Journal Entry" if last == True else None,
				"reference_name": self.reference_journal if last == True else None
			}
		])
		if save or submit:
			jv.insert(ignore_permissions=True)

			if submit:
				jv.submit()

		self.append("status_history", {
								"status": self.cheque_status,
								"transaction_date": nowdate(),
								"bank": self.deposit_bank,
								"debit_account": account1,
								"credit_account": account2,
								"journal_entry": jv.name
							})
		self.bank_changed = 1
		self.submit()
		frappe.db.commit()
		message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (jv.name, jv.name)
		msgprint(_("Journal Entry {0} created").format(comma_and(message)))
		#message = _("Journal Entry {0} created").format(comma_and(message))

		return message
	
	def make_journal_entry_jv(self, account1, journal_entry, amount, posting_date=None, party_type=None, party=None, cost_center=None, 
							save=True, submit=False, last=False):
		journalentry=frappe.get_doc("Journal Entry", journal_entry)
		naming_series = frappe.db.get_value("Company", self.company, "journal_entry_naming_series")
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = posting_date
		if naming_series:
			jv.naming_series=naming_series
		jv.company = self.company
		jv.cheque_no = self.cheque_no
		jv.cheque_date = self.cheque_date
		jv.user_remark = self.remarks or "Cheque Transaction"
		jv.multi_currency = 0
		account=[]
		accd=''
		i=0
		#credit_in_account_currency
		for acc in journalentry.accounts:
			if acc.debit_in_account_currency != 0:
				acamount=acc.debit_in_account_currency
			else:	
				acamount=acc.credit_in_account_currency

			if i==0:
				accd={				
					"account": account1,
					"party_type": None,
					"party":None,
					"cost_center": cost_center,
					"project": acc.project,
					"debit_in_account_currency": acamount if acamount > 0 else 0,
					"credit_in_account_currency": abs(acamount) if acamount < 0 else 0
					}
				account.append(accd)
			else:
				if acc.credit_in_account_currency > 0:
					accd={
					"account": acc.account,
					"party_type": acc.party_type,
					"party": acc.party,
					"cost_center": cost_center,
					"project": acc.project,
					"credit_in_account_currency": acc.credit_in_account_currency,
					"debit_in_account_currency": acc.debit_in_account_currency,
					"reference_type": "Journal Entry" if last == True else None,
					"reference_name": self.reference_journal if last == True else None
					}
				else:
					accd={
					"account": acc.account,
					"party_type": acc.party_type,
					"party": acc.party,
					"cost_center": cost_center,
					"project": acc.project,
					"credit_in_account_currency": acc.credit_in_account_currency,
					"debit_in_account_currency": acc.debit_in_account_currency,					
					}
				account.append(accd)
				if acc.party:
					account2=acc.account
			i+=1
		jv.set("accounts", account)
		#import json				
		#frappe.throw(json.dumps(account))
		#msgprint(json.dumps(account))
		if save or submit:
			jv.insert(ignore_permissions=True)

			if submit:
				jv.submit()

		self.append("status_history", {
								"status": self.cheque_status,
								"transaction_date": nowdate(),
								"bank": self.deposit_bank,
								"debit_account": account1,
								"credit_account": account2,
								"journal_entry": jv.name
							})
		self.bank_changed = 1
		self.submit()
		frappe.db.commit()
		message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (jv.name, jv.name)
		msgprint(_("Journal Entry {0} created").format(comma_and(message)))
		#message = _("Journal Entry {0} created").format(comma_and(message))

		return message
		