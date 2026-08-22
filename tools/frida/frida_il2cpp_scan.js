/**
 * Automated Frida IL2CPP Introspection & BattleManager Discovery
 * Resolves LogicBattleManager class, static fields, and live runtime instances.
 */

'use strict';

function runScan() {
    console.log('[*] =========================================================');
    console.log('[*] MLBB IL2CPP RUNTIME INTROSPECTION & BATTLEMANAGER DISCOVERY');
    console.log('[*] =========================================================');

    var liblogic = Process.findModuleByName('liblogic.so');
    var libil2cpp = Process.findModuleByName('libil2cpp.so');

    if (!liblogic || !libil2cpp) {
        console.log('[-] Required modules not found! liblogic: ' + liblogic + ', libil2cpp: ' + libil2cpp);
        return;
    }

    console.log('[+] liblogic.so base  : ' + liblogic.base + ' (size: ' + liblogic.size + ')');
    console.log('[+] libil2cpp.so base : ' + libil2cpp.base + ' (size: ' + libil2cpp.size + ')');

    function getExport(name) {
        var addr = libil2cpp.findExportByName(name);
        if (!addr) addr = liblogic.findExportByName(name);
        if (!addr) addr = Process.findExportByName(null, name);
        return addr;
    }

    var il2cpp_domain_get = getExport('il2cpp_domain_get');
    var il2cpp_domain_get_assemblies = getExport('il2cpp_domain_get_assemblies');
    var il2cpp_assembly_get_image = getExport('il2cpp_assembly_get_image');
    var il2cpp_image_get_class_count = getExport('il2cpp_image_get_class_count');
    var il2cpp_image_get_class = getExport('il2cpp_image_get_class');
    var il2cpp_class_get_name = getExport('il2cpp_class_get_name');
    var il2cpp_class_get_namespace = getExport('il2cpp_class_get_namespace');
    var il2cpp_class_get_methods = getExport('il2cpp_class_get_methods');
    var il2cpp_method_get_name = getExport('il2cpp_method_get_name');

    console.log('[*] Checking IL2CPP exported APIs: ' + (il2cpp_domain_get ? 'EXPORTS PRESENT ✅' : 'STRIPPED ⚠️'));

    var targetClasses = ['LogicBattleManager', 'LogicBattleData', 'LogicPlayer', 'LogicFighter'];
    var foundKlasses = {};

    if (il2cpp_domain_get && il2cpp_domain_get_assemblies) {
        var fn_domain_get = new NativeFunction(il2cpp_domain_get, 'pointer', []);
        var fn_domain_get_assemblies = new NativeFunction(il2cpp_domain_get_assemblies, 'pointer', ['pointer', 'pointer']);
        var fn_assembly_get_image = new NativeFunction(il2cpp_assembly_get_image, 'pointer', ['pointer']);
        var fn_class_get_name = new NativeFunction(il2cpp_class_get_name, 'pointer', ['pointer']);
        var fn_class_get_namespace = new NativeFunction(il2cpp_class_get_namespace, 'pointer', ['pointer']);
        var fn_image_get_class_count = il2cpp_image_get_class_count ? new NativeFunction(il2cpp_image_get_class_count, 'size_t', ['pointer']) : null;
        var fn_image_get_class = il2cpp_image_get_class ? new NativeFunction(il2cpp_image_get_class, 'pointer', ['pointer', 'size_t']) : null;

        var domain = fn_domain_get();
        var sizePtr = Memory.alloc(Process.pointerSize);
        var assemblies = fn_domain_get_assemblies(domain, sizePtr);
        var asmCount = sizePtr.readPointer().toInt32();
        console.log('[+] Domain assemblies count: ' + asmCount);

        for (var i = 0; i < asmCount; i++) {
            var asmPtr = assemblies.add(i * Process.pointerSize).readPointer();
            var imgPtr = fn_assembly_get_image(asmPtr);
            if (imgPtr.isNull() || !fn_image_get_class_count || !fn_image_get_class) continue;

            var classCount = fn_image_get_class_count(imgPtr);
            for (var c = 0; c < classCount; c++) {
                var klass = fn_image_get_class(imgPtr, c);
                if (klass.isNull()) continue;

                var cnamePtr = fn_class_get_name(klass);
                var cnsPtr = fn_class_get_namespace(klass);
                var cname = cnamePtr ? cnamePtr.readUtf8String() : '';
                var cns = cnsPtr ? cnsPtr.readUtf8String() : '';

                if (targetClasses.indexOf(cname) !== -1) {
                    var fullName = (cns ? cns + '.' : '') + cname;
                    console.log('[+] Found IL2CPP Class: ' + fullName + ' @ ' + klass);
                    foundKlasses[fullName] = klass;
                    foundKlasses[cname] = klass;
                }
            }
        }
    }

    // Inspect LogicBattleManager
    var mgrKlass = foundKlasses['LogicBattleManager'] || foundKlasses['Battle.LogicBattleManager'];
    if (mgrKlass) {
        console.log('\n[*] --- Inspecting LogicBattleManager Il2CppClass (' + mgrKlass + ') ---');
        
        for (var off = 0x90; off <= 0xd0; off += 8) {
            var val = mgrKlass.add(off).readPointer();
            if (!val.isNull()) {
                console.log('    klass + 0x' + off.toString(16) + ' -> ' + val);
            }
        }

        var sf_b0 = mgrKlass.add(0xb0).readPointer();
        var sf_b8 = mgrKlass.add(0xb8).readPointer();
        var sfList = [['0xb0', sf_b0], ['0xb8', sf_b8]];

        sfList.forEach(function(pair) {
            var label = pair[0];
            var sf = pair[1];
            if (!sf.isNull()) {
                try {
                    var inst = sf.readPointer();
                    console.log('[+] static_fields (at +' + label + ' = ' + sf + ') -> static_fields[0] (Instance) = ' + inst);
                    if (!inst.isNull()) {
                        var state = inst.add(0x180).readS32();
                        var frameTime = inst.add(0x19c).readU32();
                        var selfPlayer = inst.add(0x200).readPointer();
                        var localLogic = inst.add(0x0a0).readPointer();
                        var dicPlayer = inst.add(0x0a8).readPointer();
                        console.log('    ========================================');
                        console.log('    [LIVE BATTLE MANAGER INSTANCE VALIDATION]');
                        console.log('    ========================================');
                        console.log('    Instance Addr    : ' + inst);
                        console.log('    _m_eState (+0x180): ' + state + (state === 2 ? ' (IN_BATTLE ✅)' : ' (Not in battle)'));
                        console.log('    m_uiFrameTime    : ' + frameTime);
                        console.log('    m_RealSelfPlayer : ' + selfPlayer);
                        console.log('    m_LocalPlayerLogic: ' + localLogic);
                        console.log('    m_dicPlayerLogic : ' + dicPlayer);

                        if (!selfPlayer.isNull()) {
                            console.log('    [HERO VALIDATION (+0x200)]');
                            console.log('      Hero ID : ' + selfPlayer.add(0x0ac).readS32());
                            console.log('      Level   : ' + selfPlayer.add(0x0b4).readS32());
                            console.log('      HP      : ' + selfPlayer.add(0x0c8).readS32() + ' / ' + selfPlayer.add(0x0cc).readS32());
                            console.log('      Pos X,Y : ' + selfPlayer.add(0x268).readDouble().toFixed(2) + ', ' + selfPlayer.add(0x270).readDouble().toFixed(2));
                            console.log('      Camp    : ' + selfPlayer.add(0x1dc).readS32());
                        }
                    }
                } catch(e) {
                    console.log('[-] Error reading instance: ' + e);
                }
            }
        });

        // Inspect methods of LogicBattleManager to discover getter RVAs
        if (il2cpp_class_get_methods && il2cpp_method_get_name) {
            var fn_class_get_methods = new NativeFunction(il2cpp_class_get_methods, 'pointer', ['pointer', 'pointer']);
            var fn_method_get_name = new NativeFunction(il2cpp_method_get_name, 'pointer', ['pointer']);
            var iter = Memory.alloc(Process.pointerSize);
            iter.writePointer(ptr(0));

            console.log('\n[*] --- Methods of LogicBattleManager ---');
            var method;
            while (!(method = fn_class_get_methods(mgrKlass, iter)).isNull()) {
                var mName = fn_method_get_name(method).readUtf8String();
                var fnPtr = method.readPointer();
                if (mName && (mName.indexOf('LocalPlayer') !== -1 || mName.indexOf('Instance') !== -1 || mName.indexOf('BattleState') !== -1 || mName.indexOf('get_battleManager') !== -1)) {
                    var rva = fnPtr.sub(liblogic.base);
                    console.log('    Method: ' + mName + ' -> Native Addr: ' + fnPtr + ' (RVA: 0x' + rva.toString(16) + ')');
                }
            }
        }
    }

    // Inspect LogicBattleData
    var dataKlass = foundKlasses['LogicBattleData'] || foundKlasses['Battle.LogicBattleData'];
    if (dataKlass) {
        console.log('\n[*] --- Inspecting LogicBattleData Il2CppClass (' + dataKlass + ') ---');
        if (il2cpp_class_get_methods && il2cpp_method_get_name) {
            var fn_class_get_methods2 = new NativeFunction(il2cpp_class_get_methods, 'pointer', ['pointer', 'pointer']);
            var fn_method_get_name2 = new NativeFunction(il2cpp_method_get_name, 'pointer', ['pointer']);
            var iter2 = Memory.alloc(Process.pointerSize);
            iter2.writePointer(ptr(0));

            var method2;
            while (!(method2 = fn_class_get_methods2(dataKlass, iter2)).isNull()) {
                var mName2 = fn_method_get_name2(method2).readUtf8String();
                var fnPtr2 = method2.readPointer();
                if (mName2 && (mName2.indexOf('battleManager') !== -1 || mName2.indexOf('Instance') !== -1 || mName2.indexOf('Fighter') !== -1)) {
                    var rva2 = fnPtr2.sub(liblogic.base);
                    console.log('    Method: ' + mName2 + ' -> Native Addr: ' + fnPtr2 + ' (RVA: 0x' + rva2.toString(16) + ')');
                }
            }
        }
    }

    console.log('\n[*] Introspection complete.');
}

setTimeout(runScan, 100);
