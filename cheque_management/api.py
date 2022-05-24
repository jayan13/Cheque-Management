# -*- coding: utf-8 -*-
# Copyright (c) 2017, Direction and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt, cstr, nowdate, comma_and, cint
from frappe import throw, msgprint, _

def pe_before_submit(self, method):
	if self.reference_date <= nowdate():
		return
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
	if self.reference_date <= nowdate():
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

		naming_series = frappe.db.get_value("Company", self.company, "journal_entry_naming_series")
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = posting_date or nowdate()
		jv.due_date = posting_date or nowdate()
		if naming_series:
			jv.naming_series=naming_series
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
				"debit_in_account_currency": abs(amount) if amount < 0 else 0
			}
		])
		#import json				
		#frappe.throw(json.dumps(account))
		#frappe.throw(_("cost center {0}").format(cost_center))
		jv.insert(ignore_permissions=True)
		jv.submit()
		frappe.db.commit()
		return jv
#----------- journal entry payment -------------------------------------------

def jv_before_submit(self, method):
	if self.cheque_date <= nowdate():
		return
	if self.mode_of_payment=='Cheque':
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
	if self.cheque_date <= nowdate():
		return
	if self.mode_of_payment=='Cheque':
		hh_currency = erpnext.get_company_currency(self.company)
		recnotes_acc = frappe.db.get_value("Company", self.company, "receivable_notes_account")
		if not recnotes_acc:
			frappe.throw(_("Receivable Notes Account not defined in the company setup page"))
		
		crs_acc = frappe.db.get_value("Company", self.company, "cross_transaction_account")
		if not crs_acc:
			frappe.throw(_("Cross Transaction Account not defined in the company setup page"))
		#-----------------------------------------------------
		paynotes_acc = frappe.db.get_value("Company", self.company, "payable_notes_account")
		if not paynotes_acc:
			frappe.throw(_("Payable Notes Account not defined in the company setup page"))
		
		rec_acc = frappe.db.get_value("Company", self.company, "default_payable_account")
		if not rec_acc:
			frappe.throw(_("Default Payable Account not defined in the company setup page"))

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

		if party_type=='Customer':
			pgroup = frappe.db.get_value('Customer', {'customer_name': party}, ['customer_group'])
		else:
			pgroup = frappe.db.get_value('Supplier', {'supplier_name': party}, ['supplier_group'])
		
		if self.cheque_pay_type=='Receive':
			journal = make_journal_entry_jv(self, partyacc, crs_acc, self.cheque_amount, self.posting_date)

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
			rc.reference_journal = journal.name
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
			pc.party_type = self.party_type
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
	
def make_journal_entry_jv(self, account1, account2, amount, posting_date=None, party_type=None, party=None, cost_center=None):
	naming_series = frappe.db.get_value("Company", self.company, "journal_entry_naming_series")
	cost_center = frappe.db.get_value("Company", self.company, "cost_center")
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date or nowdate()
	jv.due_date = posting_date or nowdate()
	if naming_series:
		jv.naming_series=naming_series
	jv.company = self.company
	jv.cheque_no = self.cheque_no
	jv.cheque_date = self.cheque_date
	jv.user_remark = self.user_remark
	jv.multi_currency = 0
	account=[]
	accd=''
	i=0
	accu=frappe.db.get_list("Journal Entry Account",
		fields=['account', 'party_type','party','cost_center','project','sum(debit_in_account_currency) as debit','sum(credit_in_account_currency) as credit'],
		filters={'party': ['!=', ''],'parent':self.name},
		group_by='party')
	#credit_in_account_currency
	for acc in self.accounts:
		if i==0:
			accd={
				"account": account2,
				"party_type": None,
				"party": None,
				"cost_center": cost_center,
				"project": acc.project,
				"credit_in_account_currency": acc.debit_in_account_currency,
				"debit_in_account_currency": 0
				}
			account.append(accd)
			break		
		i+=1

	for acc2 in accu:
		dbit=acc2.credit-acc2.debit
		if dbit > 0:
			accd={
				"account": account1,
				"party_type": acc2.party_type,
				"party": acc2.party,
				"cost_center": cost_center,
				"project": acc2.project,
				"debit_in_account_currency": dbit,
				"credit_in_account_currency": 0,
				}
			account.append(accd)
	#import json				
	#frappe.throw(json.dumps(account))
	jv.set("accounts", account)
	jv.insert(ignore_permissions=True)
	jv.submit()
	frappe.db.commit()
	return jv

#---------  bulk update from list view pay rec--------------------------------
@frappe.whitelist()
def update_cheque_status(docnames,status,posting_date):
	import json
	docnames=json.loads(docnames)
	msg=''
	for dc in docnames:
		crec=frappe.get_doc("Receivable Cheques", dc)		
		uc_acc = frappe.db.get_value("Company", crec.company, "cheques_under_collection_account")
		ct_acc = frappe.db.get_value("Company", crec.company, "cross_transaction_account")
		notes_acc = frappe.db.get_value("Company", crec.company, "receivable_notes_account")
		if crec.payment_entry:
			rec_acc = frappe.db.get_value("Payment Entry", crec.payment_entry, "paid_from")		
			
			if status == "Cheque Deposited":
				msg+=status+" - "+dc+", "
				make_journal_entry_bulk(crec,status,posting_date,uc_acc, notes_acc, crec.amount, party_type=None, party=None, cost_center=None,save=True, submit=True, last=False) 
					
			if status == "Cheque Collected":
				msg+=status+" - "+dc+", "
				party = frappe.db.get_value("Payment Entry", crec.payment_entry, "party")
				party_type = frappe.db.get_value("Payment Entry", crec.payment_entry, "party_type")
				make_journal_entry_bulk(crec,status,posting_date,ct_acc, uc_acc, crec.amount, party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
				make_journal_entry_bulk(crec,status,posting_date,crec.deposit_bank, rec_acc, crec.amount, party_type, party, cost_center=None,save=True, submit=True, last=True)
					
			if status == "Cheque Returned":
				msg+=status+" - "+dc+", "
				make_journal_entry_bulk(crec,status,posting_date,notes_acc, uc_acc, crec.amount,party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
					
			if status == "Cheque Rejected":
				msg+=status+" - "+dc+", "
				cancel_payment_entry(crec,status,posting_date)
					
			if status == "Cheque Cancelled":
				msg+=status+" - "+dc+", "
				cancel_payment_entry(crec,status,posting_date)
		else:
			
			if status == "Cheque Deposited":
				msg+=status+" - "+dc+", "
				make_journal_entry_bulk(crec,status,posting_date,uc_acc, notes_acc, crec.amount, party_type=None, party=None, cost_center=None,save=True, submit=True, last=False) 
					
			if status == "Cheque Collected":
				msg+=status+" - "+dc+", "
				make_journal_entry_bulk(crec,status,posting_date,ct_acc, uc_acc, crec.amount, party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
				make_journal_entry_bulk_jv(crec,status,posting_date,crec.deposit_bank, crec.journal_entry, crec.amount, cost_center=None,save=True, submit=True, last=True)
					
			if status == "Cheque Returned":
				msg+=status+" - "+dc+", "
				make_journal_entry_bulk(crec,status,posting_date,notes_acc, uc_acc, crec.amount,party_type=None, party=None, cost_center=None,save=True, submit=True, last=False)
					
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
	jv.user_remark = crec.remarks or "Cheque Transaction"
	jv.multi_currency = 0
	jv.set("accounts", [
		{
			"account": account1,
			"party_type": party_type if (status == "Cheque Cancelled" or status == "Cheque Rejected") else None,
			"party": party if status == "Cheque Cancelled" else None,
			"cost_center": cost_center,
			"project": crec.project,
			"debit_in_account_currency": amount if amount > 0 else 0,
			"credit_in_account_currency": abs(amount) if amount < 0 else 0
		}, {
			"account": account2,
			"party_type": party_type if status == "Cheque Received" or status == "Cheque Collected" else None,
			"party": party if status == "Cheque Received" or status == "Cheque Collected" else None,
			"cost_center": cost_center,
			"project": crec.project,
			"credit_in_account_currency": amount if amount > 0 else 0,
			"debit_in_account_currency": abs(amount) if amount < 0 else 0,
			"reference_type": "Journal Entry" if last == True else None,
			"reference_name": crec.reference_journal if last == True else None
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
def make_journal_entry_bulk_jv(crec, status,posting_date, account1, journal_entry, amount, cost_center=None,save=True, submit=False, last=False):
	journalentry=frappe.get_doc("Journal Entry", crec.reference_journal)	
	naming_series = frappe.db.get_value("Company", crec.company, "journal_entry_naming_series")
	cost_center = frappe.db.get_value("Company", crec.company, "cost_center")
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date
	if naming_series:
		jv.naming_series=naming_series
	jv.company = crec.company
	jv.cheque_no = crec.cheque_no
	jv.cheque_date = crec.cheque_date
	jv.user_remark = crec.remarks or "Cheque Transaction"
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
				"debit_in_account_currency": acamount,
				"credit_in_account_currency": 0
				}
			account.append(accd)
		else:

			accd={
				"account": acc.account,
				"party_type": acc.party_type,
				"party": acc.party,
				"cost_center": cost_center,
				"project": acc.project,
				"credit_in_account_currency": acamount,
				"debit_in_account_currency": 0,
				"reference_type": "Journal Entry" if last == True else None,
				"reference_name": crec.reference_journal if last == True else None
				}

			account.append(accd)
			if acc.party:
					account2=acc.account
		i+=1
	jv.set("accounts", account)
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
	if crec.reference_journal:
		frappe.get_doc("Journal Entry", crec.reference_journal).cancel()
	if crec.payment_entry: 
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
	if crec.reference_journal:
		frappe.get_doc("Journal Entry", crec.reference_journal).cancel()
	if crec.journal_entry:
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
			make_journal_entry_bulk_pay(cpay,status,posting_date,notes_acc, cpay.bank,cpay.amount,party_type=None, party=None, cost_center=None,save=True, submit=True)
						
		if status == "Cheque Cancelled":
			msg+=status+" - "+dc+", "
			if cpay.payment_entry:
				cancel_payment_entry_bulk_pay(cpay,status,posting_date)
			else:
				cancel_payment_entry_bulk_pay_jv(cpay,status,posting_date)
	
	return msg

def make_journal_entry_bulk_pay(cpay,status,posting_date,account1, account2, amount, party_type=None, party=None, cost_center=None, save=True, submit=False):

	naming_series = frappe.db.get_value("Company", cpay.company, "journal_entry_naming_series")
	cost_center = frappe.db.get_value("Company", cpay.company, "cost_center")
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date
	if naming_series:
		jv.naming_series=naming_series
	jv.company = cpay.company
	jv.cheque_no = cpay.cheque_no
	jv.cheque_date = cpay.cheque_date
	jv.user_remark = cpay.remarks or "Cheque Transaction"
	jv.multi_currency = 0
	jv.set("accounts", [
			{
				"account": account1,
				"party_type": party_type if (status == "Cheque Cancelled") else None,
				"party": party if status == "Cheque Cancelled" else None,
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
