# -*- coding: utf-8 -*-
# Copyright (c) 2017, Direction and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt, cstr, nowdate, comma_and, cint, getdate
from frappe import throw, msgprint, _

def pe_before_submit(self, method):
	
	if self.reference_date and self.reference_date <= self.posting_date:
		return
	if self.mode_of_payment == "Cheque" and self.payment_type == "Receive":
		account_type=frappe.db.get_value('Account', self.paid_to, 'account_type')
		if account_type!='Bank':
			frappe.throw(_("{0} is not a bank account, Check Paid To Account must be a Back Account ").format(self.paid_to))

		notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not notes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		
		self.db_set("cheque_paid_to", self.paid_to)	
		self.db_set("paid_to", notes_acc)
	if self.mode_of_payment == "Cheque" and self.payment_type == "Pay":
		account_type=frappe.db.get_value('Account', self.paid_from, 'account_type')
		if account_type!='Bank':
			frappe.throw(_("{0} is not a bank account, Check Paid From Account must be a Back Account ").format(self.paid_from))
		notes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
		if not notes_acc:
			frappe.throw(_("Payable Notes Account not defined in the company setup page"))
		self.db_set("cheque_paid_from", self.paid_from)		
		self.db_set("paid_from", notes_acc)
		

def pe_on_submit(self, method):
	
	if self.reference_date and self.reference_date <= self.posting_date:
		return
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



#----------- journal entry payment -------------------------------------------

def jv_before_submit(self, method):
	
	if self.mode_of_payment=='Cheque':
		if self.cheque_date <= self.posting_date:
			return
		#--------------- temp fix ---
		party_type='Customer'
		party=''
		pgroup=''
		partyacc=''
		for acc in self.accounts:			
			if acc.party_type:
				party_type=acc.party_type
				partyacc=acc.account

			if acc.party:
				party=acc.party
				partyacc=acc.account

		if party=='':
			return
		#--------------- temp fix  end---

		for acc in self.accounts:
			account_type=frappe.db.get_value('Account', acc.account, 'account_type')
			if account_type=='Bank':
				if acc.debit > 0:
					self.cheque_amount=acc.debit
					self.cheque_pay_type='Receive'
					self.cheque_paid_acc=acc.account
					notes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
					if not notes_acc:
						frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
					acc.db_set("account", notes_acc)

				else:
					self.cheque_amount=acc.credit
					self.cheque_pay_type='Pay'
					self.cheque_paid_acc=acc.account
					notes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
					if not notes_acc:
						frappe.throw(_("Payable Notes Account not defined in the company setup page"))						
					acc.db_set("account", notes_acc)
			
		
def jv_on_submit(self, method):
	
	if self.mode_of_payment=='Cheque':
		if self.cheque_date <= self.posting_date:
			return

		party_type='Customer'
		party=''
		pgroup=''
		partyacc=''

		for acc in self.accounts:			
			if acc.party_type:
				party_type=acc.party_type
				partyacc=acc.account

			if acc.party:
				party=acc.party
				partyacc=acc.account
		#--------------- temp fix ---
		if party=='':
			return
		#--------------- temp fix  end ---
		
		hh_currency = erpnext.get_company_currency(self.company)
		recnotes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not recnotes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))		
		
		#-----------------------------------------------------
		paynotes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
		if not paynotes_acc:
			frappe.throw(_("Payable Notes Account not defined in the company setup page"))
		
		rec_acc = frappe.db.get_value("Company", self.company, "default_payable_account")
		if not rec_acc:
			frappe.throw(_("Default Payable Account not defined in the company setup page"))

			

		if party_type=='Customer':
			pgroup = frappe.db.get_value('Customer', {'customer_name': party}, ['customer_group'])
		else:
			pgroup = frappe.db.get_value('Supplier', {'supplier_name': party}, ['supplier_group'])
		
		if self.cheque_pay_type=='Receive':
			
			rc = frappe.new_doc("Receivable Cheques")
			rc.cheque_no = self.cheque_no 
			rc.cheque_date = self.cheque_date 
			rc.customer = party
			rc.company = self.company
			rc.currency = hh_currency
			rc.amount = self.cheque_amount
			rc.exchange_rate = 1
			rc.remarks = self.remark
			rc.deposit_bank=self.cheque_paid_acc
			rc.journal_entry=self.name
			
			rc.docstatus=1
			rc.customer_group=pgroup
			rc.cheque_status = 'Cheque Received'
			rc.set("status_history", [
				{
					"status": "Cheque Received",
					"transaction_date": nowdate(),
					"credit_account": partyacc,
					"debit_account": recnotes_acc
				}
			])
			rc.insert(ignore_permissions=True)
			rc.submit()
			message = """<a href="#Form/Receivable Cheques/%s" target="_blank">%s</a>""" % (rc.name, rc.name)
			msgprint(_("Receivable Cheque {0} created").format(comma_and(message)))

			
		if self.cheque_pay_type=='Pay':
			#amount=self.total_credit or amount
			pc = frappe.new_doc("Payable Cheques")
			pc.cheque_no = self.cheque_no 
			pc.cheque_date = self.cheque_date 
			pc.party_type = party_type
			pc.party = party
			pc.company = self.company			
			pc.currency = hh_currency
			pc.amount = self.cheque_amount
			pc.exchange_rate = 1
			pc.remarks = self.remark  
			pc.bank=self.cheque_paid_acc
			pc.journal_entry = self.name
			pc.docstatus=1
			pc.set("status_history", [
				{
					"status": "Cheque Issued",
					"transaction_date": nowdate(),
					"credit_account": paynotes_acc,
					"debit_account": partyacc
				}
			])
			pc.insert(ignore_permissions=True)
			pc.submit()
			message = """<a href="#Form/Payable Cheques/%s" target="_blank">%s</a>""" % (pc.name, pc.name)
			msgprint(_("Payable Cheque {0} created").format(comma_and(message)))

#---------  bulk update from list view pay rec--------------------------------
@frappe.whitelist()
def update_cheque_status(docnames,status,posting_date):
	import json
	docnames=json.loads(docnames)
	msg=''
	for dc in docnames:
		crec=frappe.get_doc("Receivable Cheques", dc)				
		notes_acc = frappe.db.get_value("Company", crec.company, "receivable_notes_account")

		party_type=''
		party=''

		if crec.payment_entry:
			#rec_acc = frappe.db.get_value("Payment Entry", crec.payment_entry, "paid_from")
			
			
			if status == "Cheque Realized":
				make_journal_entry_bulk(crec,status,posting_date,crec.deposit_bank, notes_acc, crec.amount, 'Customer', crec.customer, cost_center=None,save=True, submit=True, last=True)
			
			if status == "Cheque Returned":
				msg+=status+" - "+dc+", "
				#make_journal_entry_bulk(crec,status,posting_date,notes_acc, uc_acc, crec.amount,party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
				cancel_payment_entry(crec,status,posting_date)

			if status == "Cheque Rejected":
				msg+=status+" - "+dc+", "
				cancel_payment_entry(crec,status,posting_date)
					
			if status == "Cheque Cancelled":
				msg+=status+" - "+dc+", "
				cancel_payment_entry(crec,status,posting_date)
		else:
			
			if status == "Cheque Realized":
				msg+=status+" - "+dc+", "
				#make_journal_entry_bulk_jv(crec,status,posting_date,crec.deposit_bank, crec.journal_entry, crec.amount, cost_center=None,save=True, submit=True, last=True)
				make_journal_entry_bulk(crec,status,posting_date,crec.deposit_bank, notes_acc, crec.amount, 'Customer', crec.customer, cost_center=None,save=True, submit=True, last=True)
			
			if status == "Cheque Returned":
				msg+=status+" - "+dc+", "
				#make_journal_entry_bulk(crec,status,posting_date,notes_acc, uc_acc, crec.amount,party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
				cancel_payment_entry_jv(crec,status,posting_date)

			if status == "Cheque Rejected":
				msg+=status+" - "+dc+", "
				cancel_payment_entry_jv(crec,status,posting_date)
					
			if status == "Cheque Cancelled":
				msg+=status+" - "+dc+", "
				cancel_payment_entry_jv(crec,status,posting_date)	

	return msg

def make_journal_entry_bulk(crec, status,posting_date, account1, account2, amount, party_type=None, party=None, cost_center=None,save=True, submit=False, last=False):
	naming_series = frappe.db.get_value("Company", crec.company, "journal_entry_naming_series")
	cost_center = frappe.db.get_value("Company", crec.company, "cost_center")
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date
	if naming_series:
		jv.naming_series=naming_series
	jv.company = crec.company
	jv.cheque_no = crec.cheque_no
	jv.cheque_date = crec.cheque_date
	voucher=crec.payment_entry or crec.journal_entry
	if crec.journal_entry:
		postingdate=frappe.db.get_value('Journal Entry',crec.journal_entry,'posting_date')
	else:	
		postingdate=frappe.db.get_value('Payment Entry',crec.payment_entry,'posting_date')

	jv.user_remark=crec.remarks+" PDC Realization aganist "+voucher+" Date: "+ str(postingdate)+". "
	
	jv.multi_currency = 0
	jv.set("accounts", [
		{
			"account": account1,
			"party_type": None,
			"party": None,
			"cost_center": cost_center,
			"project": crec.project,
			"debit_in_account_currency": amount if amount > 0 else 0,
			"credit_in_account_currency": abs(amount) if amount < 0 else 0
		}, {
			"account": account2,
			"party_type": party_type,
			"party": party,
			"cost_center": cost_center,
			"project": crec.project,
			"credit_in_account_currency": amount if amount > 0 else 0,
			"debit_in_account_currency": abs(amount) if amount < 0 else 0,
			#"reference_type": "Journal Entry" if last == True else None,
			#"reference_name": crec.reference_journal if last == True else None
			}
	])
	if save or submit:
		jv.insert(ignore_permissions=True)

		if submit:
			jv.submit()

	
	midx=frappe.db.sql("""select max(idx) from `tabReceivable Cheques Status` where parent=%s""",(crec.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Receivable Cheques Status")
	hist.docstatus=1
	hist.parent=crec.name
	hist.parentfield='status_history'
	hist.parenttype='Receivable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.bank=crec.deposit_bank
	hist.debit_account=account1
	hist.credit_account=account2
	hist.journal_entry=jv.name
	hist.insert(ignore_permissions=True)
	frappe.db.commit()
	message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (jv.name, jv.name)
	#msgprint(_("Journal Entry {0} created").format(comma_and(message)))
	message = _("Journal Entry {0} created").format(comma_and(message))

	return message

def cancel_payment_entry(crec, status,posting_date):
	#frappe.msgprint('cancel api')
	if crec.payment_entry:
		remarks = frappe.db.get_value('Payment Entry', crec.payment_entry, 'remarks')
		remarks=remarks+'<br>'+nowdate()+' - '+status
		frappe.db.set_value('Payment Entry', crec.payment_entry,'workflow_state', 'Cancelled')
		frappe.db.set_value('Payment Entry', crec.payment_entry,'remarks', remarks)  
		frappe.get_doc("Payment Entry", crec.payment_entry).cancel()
	
	midx=frappe.db.sql("""select max(idx) from `tabReceivable Cheques Status` where parent=%s""",(crec.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Receivable Cheques Status")
	hist.docstatus=1
	hist.parent=crec.name
	hist.parentfield='status_history'
	hist.parenttype='Receivable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.bank=crec.deposit_bank
	hist.insert(ignore_permissions=True)
	message = """<a href="#Form/Payment Entry/%s" target="_blank">%s</a>""" % (crec.payment_entry, crec.payment_entry)
	#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))
	message = _("Payment Entry {0} Cancelled").format(comma_and(message))

	return message
def cancel_payment_entry_jv(crec, status,posting_date):
	
	if crec.journal_entry:
		remark = frappe.db.get_value('Journal Entry', crec.journal_entry, 'remark')
		remark=remark+'<br>'+nowdate()+' - '+status
		frappe.db.set_value('Journal Entry', crec.journal_entry,'workflow_state', 'Cancelled')
		frappe.db.set_value('Journal Entry', crec.journal_entry,'remark', remark)	
		frappe.get_doc("Journal Entry", crec.journal_entry).cancel()
	
	midx=frappe.db.sql("""select max(idx) from `tabReceivable Cheques Status` where parent=%s""",(crec.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Receivable Cheques Status")
	hist.docstatus=1
	hist.parent=crec.name
	hist.parentfield='status_history'
	hist.parenttype='Receivable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.bank=crec.deposit_bank
	hist.insert(ignore_permissions=True)
	message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (crec.reference_journal, crec.reference_journal)
	#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))
	message = _("Payment Entry {0} Cancelled").format(comma_and(message))

	return message
#------------ bulk update list view pay paid ------------
@frappe.whitelist()
def update_cheque_status_pay(docnames,status,posting_date):
	import json
	docnames=json.loads(docnames)
	msg=''
	for dc in docnames:
		cpay=frappe.get_doc("Payable Cheques", dc)
		notes_acc = frappe.db.get_value("Company", cpay.company, "payable_notes_account")
		ec_acc = frappe.db.get_value("Company", cpay.company, "default_payable_account")

		if status == "Cheque Deducted":
			msg+=status+" - "+dc+", "
			make_journal_entry_bulk_pay(cpay,status,posting_date,notes_acc, cpay.bank,cpay.amount,cpay.party_type, cpay.party, cost_center=None,save=True, submit=True)
						
		if status == "Cheque Cancelled":
			msg+=status+" - "+dc+", "
			if cpay.payment_entry:
				cancel_payment_entry_bulk_pay(cpay,status,posting_date)
			else:
				cancel_payment_entry_bulk_pay_jv(cpay,status,posting_date)
	
	return msg

def make_journal_entry_bulk_pay(cpay,status,posting_date,account1, account2, amount, party_type=None, party=None, cost_center=None, save=True, submit=False):

	naming_series = frappe.db.get_value("Company", cpay.company, "payment_journal_entry_naming_series")
	cost_center = frappe.db.get_value("Company", cpay.company, "cost_center")
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date
	if naming_series:
		jv.naming_series=naming_series
	jv.company = cpay.company
	jv.cheque_no = cpay.cheque_no
	jv.cheque_date = cpay.cheque_date
	voucher=cpay.payment_entry or cpay.journal_entry
	if cpay.journal_entry:
		postingdate=frappe.db.get_value('Journal Entry',cpay.journal_entry,'posting_date')
	else:	
		postingdate=frappe.db.get_value('Payment Entry',cpay.payment_entry,'posting_date')

	jv.user_remark=cpay.remarks+" PDC Realization aganist "+voucher+" Date: "+str(postingdate)+". "
	jv.multi_currency = 0
	jv.set("accounts", [
			{
				"account": account1,
				"party_type": party_type if (status == "Cheque Deducted") else None,
				"party": party if status == "Cheque Deducted" else None,
				"cost_center": cost_center,
				"project": cpay.project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0
			}, {
				"account": account2,
				"party_type": party_type if status == "Cheque Issued" else None,
				"party": party if status == "Cheque Issued" else None,
				"cost_center": cost_center,
				"project": cpay.project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0
			}
		])
	if save or submit:
		jv.insert(ignore_permissions=True)

		if submit:
			jv.submit()

	midx=frappe.db.sql("""select max(idx) from `tabPayable Cheques Status` where parent=%s""",(cpay.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Payable Cheques Status")
	hist.docstatus=1
	hist.parent=cpay.name
	hist.parentfield='status_history'
	hist.parenttype='Payable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.debit_account=account1
	hist.credit_account=account2
	hist.journal_entry=jv.name
	hist.insert(ignore_permissions=True)
	frappe.db.commit()
	message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (jv.name, jv.name)
	msgprint(_("Journal Entry {0} created").format(comma_and(message)))
	#message = _("Journal Entry {0} created").format(comma_and(message))
		
	return message

def cancel_payment_entry_bulk_pay(cpay,status,posting_date):
	if cpay.payment_entry:
		remarks = frappe.db.get_value('Payment Entry', cpay.payment_entry, 'remarks')
		remarks=remarks+'<br>'+nowdate()+' - '+status
		frappe.db.set_value('Payment Entry', cpay.payment_entry,'remarks', remarks)
		frappe.db.set_value('Payment Entry', cpay.payment_entry,'workflow_state', 'Cancelled')  
		frappe.get_doc("Payment Entry", cpay.payment_entry).cancel()
				
	midx=frappe.db.sql("""select max(idx) from `tabPayable Cheques Status` where parent=%s""",(cpay.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Payable Cheques Status")
	hist.docstatus=1
	hist.parent=cpay.name
	hist.parentfield='status_history'
	hist.parenttype='Payable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.bank=cpay.bank
	hist.insert(ignore_permissions=True)

	message = """<a href="#Form/Payment Entry/%s" target="_blank">%s</a>""" % (cpay.payment_entry, cpay.payment_entry)
	#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))

	return message
def cancel_payment_entry_bulk_pay_jv(cpay,status,posting_date):
	if cpay.journal_entry:
		remark = frappe.db.get_value('Journal Entry', cpay.journal_entry, 'remark')
		remark=remark+'<br>'+nowdate()+' - '+status
		frappe.db.set_value('Journal Entry', cpay.journal_entry,'remark', remark)
		frappe.db.set_value('Journal Entry', cpay.journal_entry,'workflow_state', 'Cancelled')
		frappe.get_doc("Journal Entry", cpay.journal_entry).cancel()

	midx=frappe.db.sql("""select max(idx) from `tabPayable Cheques Status` where parent=%s""",(cpay.name))
	curidx=1
	if midx and midx[0][0] is not None:
		curidx = cint(midx[0][0])+1

	hist=frappe.new_doc("Payable Cheques Status")
	hist.docstatus=1
	hist.parent=cpay.name
	hist.parentfield='status_history'
	hist.parenttype='Payable Cheques'
	hist.status=status
	hist.idx=curidx
	hist.transaction_date=posting_date
	hist.bank=cpay.bank
	hist.insert(ignore_permissions=True)

	message = """<a href="#Form/Journal Entry/%s" target="_blank">%s</a>""" % (cpay.journal_entry, cpay.journal_entry)
	#msgprint(_("Payment Entry {0} Cancelled").format(comma_and(message)))

	return message

@frappe.whitelist()
def get_journal_naming_series():
	nm=frappe.db.get_list('Property Setter',filters={'doc_type': 'Journal Entry','field_name': 'naming_series'},fields=['value'],pluck='value')
	res=''
	if nm:
		res=nm[0].splitlines()

	return res

def jv_cancel(self, method):
	
	pay=frappe.db.get_value('Payable Cheques', {'journal_entry': self.name}, ['name'])
	rec=frappe.db.get_value('Receivable Cheques', {'journal_entry': self.name}, ['name'])
	if pay:
		
		cpay = frappe.get_doc("Payable Cheques",pay)
		midx=frappe.db.sql("""select max(idx) from `tabPayable Cheques Status` where parent=%s""",(cpay.name))
		curidx=1
		if midx and midx[0][0] is not None:
			curidx = cint(midx[0][0])+1

		hist=frappe.new_doc("Payable Cheques Status")
		hist.docstatus=1
		hist.parent=cpay.name
		hist.parentfield='status_history'
		hist.parenttype='Payable Cheques'
		hist.status="Cheque Cancelled"
		hist.idx=curidx
		hist.transaction_date=self.posting_date
		hist.bank=cpay.bank
		hist.insert(ignore_permissions=True)
		if cpay.cheque_status != 'Cheque Cancelled':
			frappe.db.set_value('Payable Cheques', pay, 'cheque_status', 'Cheque Cancelled')
			frappe.db.set_value('Payable Cheques', pay, 'docstatus', '2')
	elif rec:
		
		
		crec=frappe.get_doc("Receivable Cheques", rec)
		midx=frappe.db.sql("""select max(idx) from `tabReceivable Cheques Status` where parent=%s""",(crec.name))
		curidx=1
		if midx and midx[0][0] is not None:
			curidx = cint(midx[0][0])+1

		hist=frappe.new_doc("Receivable Cheques Status")
		hist.docstatus=1
		hist.parent=crec.name
		hist.parentfield='status_history'
		hist.parenttype='Receivable Cheques'
		hist.status="Cheque Cancelled"
		hist.idx=curidx
		hist.transaction_date=self.posting_date
		hist.bank=crec.deposit_bank
		hist.insert(ignore_permissions=True)
		if crec.cheque_status != 'Cheque Cancelled':
			frappe.db.set_value('Receivable Cheques', rec, 'cheque_status', 'Cheque Cancelled')
			frappe.db.set_value('Receivable Cheques', rec, 'docstatus', '2')


def pe_cancel(self, method):
	#frappe.msgprint('cancel hook')	
	pay=frappe.db.get_value('Payable Cheques', {'payment_entry': self.name}, ['name'])
	rec=frappe.db.get_value('Receivable Cheques', {'payment_entry': self.name}, ['name'])

	if pay:
		cpay = frappe.get_doc("Payable Cheques",pay)
		midx=frappe.db.sql("""select max(idx) from `tabPayable Cheques Status` where parent=%s""",(cpay.name))
		curidx=1
		if midx and midx[0][0] is not None:
			curidx = cint(midx[0][0])+1

		hist=frappe.new_doc("Payable Cheques Status")
		hist.docstatus=1
		hist.parent=cpay.name
		hist.parentfield='status_history'
		hist.parenttype='Payable Cheques'
		hist.status="Cheque Cancelled"
		hist.idx=curidx
		hist.transaction_date=self.posting_date
		hist.bank=cpay.bank
		hist.insert(ignore_permissions=True)
		if cpay.cheque_status != 'Cheque Cancelled':
			frappe.db.set_value('Payable Cheques', pay, 'cheque_status', 'Cheque Cancelled')
			frappe.db.set_value('Payable Cheques', pay, 'docstatus', '2')
	elif rec:
		
		crec=frappe.get_doc("Receivable Cheques", rec)
		midx=frappe.db.sql("""select max(idx) from `tabReceivable Cheques Status` where parent=%s""",(crec.name))
		curidx=1
		if midx and midx[0][0] is not None:
			curidx = cint(midx[0][0])+1

		hist=frappe.new_doc("Receivable Cheques Status")
		hist.docstatus=1
		hist.parent=crec.name
		hist.parentfield='status_history'
		hist.parenttype='Receivable Cheques'
		hist.status="Cheque Cancelled"
		hist.idx=curidx
		hist.transaction_date=self.posting_date
		hist.bank=crec.deposit_bank
		hist.insert(ignore_permissions=True)
		if crec.cheque_status != 'Cheque Cancelled':
			frappe.db.set_value('Receivable Cheques', rec, 'cheque_status', 'Cheque Cancelled')
			frappe.db.set_value('Receivable Cheques', rec, 'docstatus', '2')
