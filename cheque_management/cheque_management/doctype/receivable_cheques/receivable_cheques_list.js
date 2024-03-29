﻿// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Receivable Cheques Status'] = {
	add_fields: ["cheque_status", "transaction_date", "bank", "journal_entry", "payment_entry"],
	get_indicator: function(doc) {
		if(cheque_status=="Cheque Received") {
			return [__("Cheque Received"), "lightblue", "cheque_status,=,'Cheque Received'"];
		} 
		if(cheque_status=="Cheque Deposited") {
			return [__("Cheque Deposited"), "blue", "cheque_status,=,'Cheque Deposited'"];
		} 
		if(cheque_status=="Cheque Collected") {
			return [__("Cheque Collected"), "green", "cheque_status,=,'Cheque Collected'"];
		}
		if(cheque_status=="Cheque Realized") {
			return [__("Cheque Realized"), "green", "cheque_status,=,'Cheque Realized'"];
		} 
		if(cheque_status=="Cheque Returned") {
			return [__("Cheque Returned"), "orange", "cheque_status,=,'Cheque Returned'"];
		} 
		if(cheque_status=="Cheque Rejected") {
			return [__("Cheque Rejected"), "red", "cheque_status,=,'Cheque Rejected'"];
		} 
		if(cheque_status=="Cheque Cancelled") {
			return [__("Cheque Cancelled"), "black", "cheque_status,=,'Cheque Cancelled'"];
		} 
 	}
};

frappe.listview_settings['Receivable Cheques'] = {

	onload(listview) {

		listview.page.actions.find('[data-label="Delete"]').parent().css("display", "none");		

		 listview.page.actions.find('[data-label="Cheque Collected"]').click(function()
		 {
			
			const docnames1 = listview.get_checked_items(true).map(docname => docname.toString());
			
			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
						frappe.call({
							method: "cheque_management.api.update_cheque_status",
							freeze: true,
							args: {
								docnames:docnames1,
								status:"Cheque Collected",
								posting_date: values.posting_date
							},
							callback: function(r) {
								console.log(r.message);
							}
						});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
			
		 });

		 listview.page.actions.find('[data-label="Cheque Realized"]').click(function()
		 {
			
			const docnames1 = listview.get_checked_items(true).map(docname => docname.toString());
			
			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
						frappe.call({
							method: "cheque_management.api.update_cheque_status",
							freeze: true,
							args: {
								docnames:docnames1,
								status:"Cheque Realized",
								posting_date: values.posting_date
							},
							callback: function(r) {
								console.log(r.message);
							}
						});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
			
		 });

		 listview.page.actions.find('[data-label="Cheque Deposited"]').click(function()
		 {
			
			const docnames2 = listview.get_checked_items(true).map(docname => docname.toString());
			
			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
					frappe.call({
						method: "cheque_management.api.update_cheque_status",
						freeze: true,
						args: {
							docnames:docnames2,
							status:"Cheque Deposited",
							posting_date: values.posting_date
						},
						callback: function(r) {
							console.log(r.message);
						}
					});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
			
		 });
		 listview.page.actions.find('[data-label="Cheque Returned"]').click(function()
		 {
			
			const docnames3 = listview.get_checked_items(true).map(docname => docname.toString());
			
			
			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
					frappe.call({
						method: "cheque_management.api.update_cheque_status",
						freeze: true,
						args: {
							docnames:docnames3,
							status:"Cheque Returned",
							posting_date: values.posting_date
						},
						callback: function(r) {
							console.log(r.message);
						}
					});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
			
		 });

		 listview.page.actions.find('[data-label="Cheque Rejected"]').click(function()
		 {
			
			const docnames4 = listview.get_checked_items(true).map(docname => docname.toString());
			

			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
					frappe.call({
						method: "cheque_management.api.update_cheque_status",
						freeze: true,
						args: {
							docnames:docnames4,
							status:"Cheque Rejected",
							posting_date: values.posting_date
						},
						callback: function(r) {
							console.log(r.message);
						}
					});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
			
		 });
		 listview.page.actions.find('[data-label="Cheque Cancelled"]').click(function()
		 {
			
			const docnames5 = listview.get_checked_items(true).map(docname => docname.toString());
			

			frappe.prompt([
				{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}
				],
				function(values){
					
					frappe.call({
						method: "cheque_management.api.update_cheque_status",
						freeze: true,
						args: {
							docnames:docnames5,
							status:"Cheque Cancelled",
							posting_date: values.posting_date
						},
						callback: function(r) {
							console.log(r.message);
						}
					});
					
						
				},
				__("Transaction Posting Date"),
				__("Confirm")
			);
		 });
   }
 }
