# -*- coding: utf-8 -*-
# Copyright (c) 2017, Direction and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr, nowdate, comma_and, getdate ,cint
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
	def on_trash(self):
		if self.payment_entry:			
			if frappe.db.get_value('Payment Entry', {'name':self.payment_entry,'docstatus':'1'}, 'name'):
				frappe.throw(_(" Cheque entry have associated payment entry {0} , please cancel payment entry").format(self.payment_entry))
		if self.journal_entry:
			if frappe.db.get_value('Journal Entry', {'name':self.payment_entry,'docstatus':'1'}, 'name'):
				frappe.throw(_(" Cheque entry have associated journal entry {0} , please cancel journal entry").format(self.journal_entry))

	@frappe.whitelist()
	def on_cancel(self):
		if self.payment_entry:			
			if frappe.db.get_value('Payment Entry', {'name':self.payment_entry,'docstatus':'1'}, 'name'):
				frappe.throw(_(" Cheque entry have associated payment entry {0} , please cancel payment entry").format(self.payment_entry))
		if self.journal_entry:
			if frappe.db.get_value('Journal Entry', {'name':self.payment_entry,'docstatus':'1'}, 'name'):
				frappe.throw(_(" Cheque entry have associated journal entry {0} , please cancel journal entry").format(self.journal_entry))


	@frappe.whitelist()
	def on_update(self):
		notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not notes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		elif len(notes_acc) < 4:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))

		party_type=''
		party=''

		if self.payment_entry:
			rec_acc = frappe.db.get_value("Payment Entry", self.payment_entry, "paid_from")			
			if self.cheque_status == "Cheque Realized":
				self.make_journal_entry(self.deposit_bank, notes_acc, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)
			
			if self.cheque_status == "Cheque Cancelled":
				self.cancel_payment_entry()
			
			if self.cheque_status == "Cheque Returned":
				self.make_journal_entry(self.deposit_bank, notes_acc, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)	
				self.make_journal_entry_ret(rec_acc,self.deposit_bank, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)

				#self.cancel_payment_entry()
			if self.cheque_status == "Cheque Rejected":
				#msgprint("rejected")
				self.cancel_payment_entry()
		else:
			
			if self.cheque_status == "Cheque Realized":
				self.make_journal_entry(self.deposit_bank, notes_acc, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)

			if self.cheque_status == "Cheque Cancelled":
				self.cancel_payment_entry_jv()
			
			if self.cheque_status == "Cheque Returned":
				self.make_journal_entry(self.deposit_bank, notes_acc, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)
				def_recv=frappe.db.get_value("Company", self.company, "default_receivable_account")
				self.make_journal_entry_ret(def_recv,self.deposit_bank, self.amount, self.posting_date, 'Customer', self.customer, cost_center=None, 
						save=True, submit=True, last=True)
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
		
		if self.payment_entry:
			docstatus=frappe.db.get_value('Payment Entry', self.payment_entry, 'docstatus')
			if docstatus!=2:
				remarks = frappe.db.get_value('Payment Entry', self.payment_entry, 'remarks')
				remarks=remarks+'<br>'+str(nowdate())+' - '+str(self.cheque_status)
				frappe.db.set_value('Payment Entry', self.payment_entry,'remarks', remarks)
				frappe.db.set_value('Payment Entry', self.payment_entry,'workflow_state', 'Cancelled')
				frappe.get_doc("Payment Entry", self.payment_entry).cancel()			
		else:	
			self.append("status_history", {
									"status": self.cheque_status,
									"transaction_date": nowdate(),
									"bank": self.deposit_bank
								})
			self.bank_changed = 1
			#self.submit()
			self.save(ignore_permissions=True,ignore_version=True)

			frappe.db.set_value('Receivable Cheques', self.name, 'bank_changed', '1')

		

		message = """<a href="#Form/Payment Entry/%s" target="_blank">%s</a>""" % (self.payment_entry, self.payment_entry)
		#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))
		message = _("Payment Entry {0} Cancelled").format(comma_and(message))

		return message
	def cancel_payment_entry_jv(self):
		
		if self.journal_entry:
			docstatus=frappe.db.get_value('Journal Entry', self.journal_entry, 'docstatus')
			if docstatus!=2:
				remark = frappe.db.get_value('Journal Entry', self.journal_entry, 'remark')
				remark=remark+'<br>'+str(nowdate())+' - '+str(self.cheque_status)
				frappe.db.set_value('Journal Entry', self.journal_entry,'remark', remark)
				frappe.db.set_value('Journal Entry', self.journal_entry,'workflow_state', 'Cancelled')
				frappe.get_doc("Journal Entry", self.journal_entry).cancel()
		else:
			self.append("status_history", {
									"status": self.cheque_status,
									"transaction_date": nowdate(),
									"bank": self.deposit_bank
								})
			self.bank_changed = 1
			#self.submit()
			self.save(ignore_permissions=True,ignore_version=True)
		message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (self.journal_entry, self.journal_entry)
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
		#jv.user_remark = self.remarks or "Cheque Transaction"
		voucher=self.payment_entry or self.journal_entry
		if self.journal_entry:
			postingdate=frappe.db.get_value('Journal Entry',self.journal_entry,'posting_date')
		else:	
			postingdate=frappe.db.get_value('Payment Entry',self.payment_entry,'posting_date')
		jv.user_remark=self.remarks+" PDC Realization aganist "+voucher+" Date: "+ str(postingdate)+". "

		jv.multi_currency = 0
		jv.set("accounts", [
			{
				"account": account1,
				"party_type": None,
				"party": None,
				"cost_center": cost_center,
				"project": self.project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0
			}, {
				"account": account2,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center,
				"project": self.project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				#"reference_type": "Journal Entry" if last == True else None,
				#"reference_name": self.reference_journal if last == True else None
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

	def make_journal_entry_ret(self, account1, account2, amount, posting_date=None, party_type=None, party=None, cost_center=None, 
							save=True, submit=False, last=False):
		naming_series = frappe.db.get_value("Company", self.company, "journal_entry_ret_naming_series")
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")	
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = posting_date or nowdate()
		jv.company = self.company
		jv.cheque_no = self.cheque_no
		jv.cheque_date = self.cheque_date
		if naming_series:
			jv.naming_series=naming_series
		#jv.user_remark = self.remarks or "Cheque Transaction"
		voucher=self.payment_entry or self.journal_entry
		if self.journal_entry:
			postingdate=frappe.db.get_value('Journal Entry',self.journal_entry,'posting_date')
		else:	
			postingdate=frappe.db.get_value('Payment Entry',self.payment_entry,'posting_date')
		jv.user_remark=self.remarks+" PDC Return aganist "+voucher+" Date: "+ str(postingdate)+". "

		jv.multi_currency = 0
		jv.set("accounts", [
			{
				"account": account1,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center,
				"project": self.project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0
			}, {
				"account": account2,				
				"party_type": None,
				"party": None,
				"cost_center": cost_center,
				"project": self.project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				#"reference_type": "Journal Entry" if last == True else None,
				#"reference_name": self.reference_journal if last == True else None
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
		
		