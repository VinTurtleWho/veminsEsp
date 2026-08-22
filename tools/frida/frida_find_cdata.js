'use strict';

function directMemoryScan() {
    console.log('[*] Performing direct Il2CppClass memory scan...');
    var targetClasses = ['CData_Hero', 'CData_Skill', 'CData_Effect', 'CData_EquipBase'];
    var foundKlasses = {};

    var ranges = Process.enumerateRanges('r--').concat(Process.enumerateRanges('rw-'));

    targetClasses.forEach(function(targetName) {
        if (foundKlasses[targetName]) return;

        var hexBytes = [];
        for (var i = 0; i < targetName.length; i++) {
            var hex = targetName.charCodeAt(i).toString(16);
            if (hex.length < 2) hex = '0' + hex;
            hexBytes.push(hex);
        }
        hexBytes.push('00');
        var strPattern = hexBytes.join(' ');

        var strMatches = [];
        ranges.forEach(function(r) {
            if (r.size > 0x8000000) return;
            try {
                Memory.scanSync(r.base, r.size, strPattern).forEach(function(m) {
                    strMatches.push(m.address);
                });
            } catch(e) {}
        });

        strMatches.forEach(function(sAddr) {
            var pVal = BigInt(sAddr.toString());
            var bytes = [];
            for (var b = 0; b < 8; b++) {
                var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
                if (byteHex.length < 2) byteHex = '0' + byteHex;
                bytes.push(byteHex);
            }
            var pPattern = bytes.join(' ');

            ranges.forEach(function(r) {
                if (r.size > 0x8000000) return;
                try {
                    Memory.scanSync(r.base, r.size, pPattern).forEach(function(m) {
                        var candKlass = m.address.sub(0x10);
                        try {
                            var namePtr = candKlass.add(0x10).readPointer();
                            if (namePtr.equals(sAddr)) {
                                foundKlasses[targetName] = candKlass;
                            }
                        } catch(e) {}
                    });
                } catch(e) {}
            });
        });
    });

    console.log('\n[*] =========================================================');
    console.log('[*] RESOLVED CDATA TABLESTREAM INSTANCES');
    console.log('[*] =========================================================');

    var resolvedInstances = {};

    targetClasses.forEach(function(targetName) {
        var klass = foundKlasses[targetName];
        if (!klass) {
            console.log('[-] Target class NOT found: ' + targetName);
            return;
        }

        console.log('\n[+] Class: ' + targetName + ' (Il2CppClass @ ' + klass + ')');

        var candidateOffsets = [0xb0, 0xb8, 0xa8, 0xc0];
        var sfPtr = ptr(0);
        var instancePtr = ptr(0);

        for (var idx = 0; idx < candidateOffsets.length; idx++) {
            var off = candidateOffsets[idx];
            try {
                var candidateSf = klass.add(off).readPointer();
                if (!candidateSf.isNull() && candidateSf.compare(ptr(0x10000000)) > 0) {
                    var candInst = candidateSf.add(0x8).readPointer();
                    if (!candInst.isNull() && candInst.compare(ptr(0x10000000)) > 0) {
                        sfPtr = candidateSf;
                        instancePtr = candInst;
                        console.log('    • static_fields (klass + 0x' + off.toString(16) + '): ' + sfPtr);
                        console.log('    • m_Instance    (static_fields + 0x8)        : ' + instancePtr);
                        break;
                    }
                }
            } catch(e) {}
        }

        if (!instancePtr.isNull()) {
            resolvedInstances[targetName] = {
                klass: klass.toString(),
                static_fields: sfPtr.toString(),
                instance: instancePtr.toString()
            };
        }
    });

    console.log('\n[*] =========================================================');
    console.log('[*] JSON EXPORT FOR CDATA STATIC POINTERS:');
    console.log(JSON.stringify(resolvedInstances, null, 2));
    console.log('[*] =========================================================\n');
}

setTimeout(directMemoryScan, 100);
