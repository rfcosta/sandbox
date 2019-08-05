// These functions will be tacked onto the GlideRecord object when we new it.
// You can add functions and properties to existing objects in this manner
// The "this" variable is actually the GlideRecord object!

GlideRecord.prototype.toObjectList = function() {
	var objectList = [];
	// loop through all the records and create the object array
	while(this.next()) {
		objectList.push(this.toObject(this));
	}
	this.restoreLocation(); // set it back to the beginning so that we can use if for other things
	return objectList;
};

// Turn a single GlideRecord record into an object
GlideRecord.prototype.toObject = function(record) {

	var recordToPackage = record || this;
	var packageToSend = {};
	for (var property in recordToPackage) {
		var pValue         = recordToPackage[property].getValue();
		var pDisplayValue  = recordToPackage[property].getDisplayValue();
		var pString = recordToPackage[property].toString();

		if ('function' != typeof recordToPackage[property] && pDisplayValue) {
			try {
				if ( this.isSysId( pString ) && (pDisplayValue != pString) ) {
					packageToSend[property] = { sys_id: pString, displayValue: pDisplayValue};
				}
				else if ( this.isDate( pString ) ) {
					var epoch = new GlideDateTime( recordToPackage[property] ).getNumericValue();
					packageToSend[ property ] = { epoch: epoch, datetime: pString };
				}
				else if (this.isBoolean( pString )) {
					packageToSend[ property ] = (pString == 'true');
				}
				else if (!isNaN( pString )) {
					packageToSend[ property ] = Number( pString );
				}
				else if ( (pDisplayValue != pString) ) {
					packageToSend[property] = { value: pString, displayValue: pDisplayValue};
				}
				else {
					//packageToSend[property] = pString;
					packageToSend[property] = pValue;

				}
			}
			catch(err){}
		}
	}
	return packageToSend;
};

GlideRecord.prototype.isSysId = function(value) {
	var sys_id_pattern = new RegExp('^[0123456789abcdef]{32}$');
	//gs.print("isSysId: " + value + " = " + sys_id_pattern.test(value.toString()).toString());
	return sys_id_pattern.test(value);
};

GlideRecord.prototype.isBoolean = function(value) {
	var boolean_pattern = new RegExp('^(true|false)$');
	return boolean_pattern.test(value);
};


GlideRecord.prototype.isDate = function(property) {
	if ( !property ) {
		return false;
	}
	var gdt = new GlideDateTime(property);
	//gs.print("isDate: " + property + " = " + ( gdt.isValid() ).toString());
	return gdt.isValid();
};

// Based on script include published at
// Ref: https://community.servicenow.com/community?id=community_blog&sys_id=b96c2ea1dbd0dbc01dcaf3231f9619b9

var PRINT = function(m) {

};

var QLIMIT = 2;
var QALRT = 'source=Service Health Portal' +
	'^stateINOpen,Reopen,Flapping' +
	'^sys_created_on>=javascript:gs.beginningOfLast30Minutes()^OR' +
	'sys_updated_on>=javascript:gs.beginningOfLast30Minutes()^OR' +
	'last_remote_time>=javascript:gs.beginningOfLast30Minutes()^OR' +
	'last_event_time>=javascript:gs.beginningOfLast30Minutes() '
;
var TALRT = 'em_alert';
var DATAO = { incidents: {}, alerts: {} };

var alrt = new GlideRecord(TALRT);
if (QLIMIT > 0) {
	alrt.setLimit(QLIMIT);
}

alrt.addEncodedQuery(QALRT);
alrt.query();
var NALRT = alrt.getRowCount();
gs.print("Number of alerts for the last 30 minutes is " + NALRT.toString());
while (alrt.next()) {
// 	gs.print("DEBUG- ALERT: " + alrt.number + " | INCIDENT: " + alrt.incident + " | typeof INCIDENT: " + typeof alrt.incident);

	var alrt_obj = alrt.toObject();
// 	DATAO.alerts.push(alrt_obj);
	DATAO.alerts[alrt_obj.number] = alrt_obj;

	var inc = new GlideRecord('incident');
	inc.addQuery("sys_id", alrt.incident.toString());
	inc.query();
	if (inc.next()) {
		var inc_obj = inc.toObject();
		var INCNUMBER = inc_obj.number;
		gs.print("ALERT: " + alrt_obj.number + " | INCIDENT: " + alrt.incident + ' ' + alrt_obj.incident + ' ' + INCNUMBER);

		if (DATAO.incidents.hasOwnProperty(INCNUMBER)) {
			DATAO.incidents[INCNUMBER].alerts.push(alrt_obj.number);
		}
		else {
			inc_obj['alerts'] = [alrt_obj.number];
			DATAO.incidents[INCNUMBER] = inc_obj;
		}
	}

}

gs.print("******");
gs.print(JSON.stringify(DATAO));
gs.print("******");
gs.print(JSUtil.describeObject(DATAO));
gs.print("******");
