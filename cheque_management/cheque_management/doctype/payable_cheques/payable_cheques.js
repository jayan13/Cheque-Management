// Copyright (c) 2017, Direction and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payable Cheques', {
	onload: function(frm) {
		// formatter for Payable Cheques Status
		//frm.page.actions_btn_group.show();
		frm.set_indicator_formatter('cheque_status',
			function(doc) { 
				if(doc.cheque_status=="Cheque Issued") {	return "lightblue"}
				if(doc.cheque_status=="Cheque Deducted") {	return "green"}
				if(doc.cheque_status=="Cheque Cancelled") {	return "black"}
		})
	},
	before_workflow_action:async (frm) =>{
		let promise = new Promise((resolve,reject) =>{		
		frappe.confirm("Do you want to update check status", () => resolve(), () => reject());
		});
		await promise.catch((err)=>frappe.throw(err));
		
		},
	refresh: function(frm) {
		//frm.page.actions_btn_group.show();
		setTimeout(() => {
			frm.remove_custom_button('Cancel');	
			$('[data-label="Amend"]').hide();								
			}, 20);
		if(frm.doc.cheque_status=="Cheque Issued") {
			frm.set_df_property("bank", 'read_only', 0);
		} else { frm.set_df_property("bank", 'read_only', 1); }
		frm.set_df_property("bank", 'reqd', 1);
		var chq_sts = "";
		$.each(frm.doc["status_history"], function(i, row) {
			chq_sts = row.status;
		});
		if(frm.doc.cheque_status) {
			if (chq_sts!=frm.doc.cheque_status) {  
				frm.page.actions_btn_group.hide();
				if (frm.doc.cheque_status=="Cheque Cancelled") {
					frm.call('on_update').then(result => {
							frm.page.actions_btn_group.show();
							frm.reload_doc();
					}); 
				}
				else {
					frappe.prompt([
						{'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': 'Posting Date', 'reqd': 1}  
						],
						function(values){
							if (values) {
								frm.doc.posting_date = values.posting_date;
								frm.call('on_update').then(result => {
										frm.page.actions_btn_group.show();
										frm.reload_doc();
								}); 
							}
						},
						__("Transaction Posting Date"),
						__("Confirm")
					);
				}
			}
		}
	}
});
cur_frm.fields_dict.bank.get_query = function(doc) {
	return {
		filters: [
			["Account", "account_type", "=", "Bank"],
			["Account", "root_type", "=", "Asset"],
			["Account", "is_group", "=",0],
			["Account", "company", "=", doc.company]
		]
	}
}