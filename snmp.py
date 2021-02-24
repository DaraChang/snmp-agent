# SNMP agent backend e.g. Agent access to Managed Objects
# python 3.6.7
from pysnmp.smi import builder, instrum, exval, compiler, view
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import context, cmdrsp
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.proto import api
from pysmi import debug
from pysnmp.smi.rfc1902 import ObjectIdentity
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading

# Create SNMP engine
snmpEngine = engine.SnmpEngine()

# 按下connect鈕，創建第二個線程負責連線
def press_connect():
    switchButtonState()
    th_connect = threading.Thread(target = connect_to_server)
    th_connect.setDaemon(True)
    th_connect.start()  # 守護執行緒
    #th_disconnect = threading.Thread(target = stopit)
    #th_disconnect.setDaemon(True)
    #th_disconnect.start()
    #connect_to_server()

# 連線
def connect_to_server():
    global snmpEngine
    snmpEngine = engine.SnmpEngine()
    # GUI變數
    ip_addr = ip_entry.get()
    port_num = port_entry.get()
    global model_name
    model_name = model_combo.get() + "-MIB"
    
    # Setup UDP over IPv4 transport endpoint
    config.addTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpTransport().openServerMode((ip_addr, int(port_num)))
    )

    # SNMPv2c setup
    # "my-area" -> user name / "public" -> community name
    config.addV1System(snmpEngine, "my-area", "public")

    config.addContext(snmpEngine, "")

    # Allow full MIB access for this user / securityModels at VACM
    config.addVacmUser(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6, 1, 4, 1, 8691))

    # Create an SNMP context
    snmpContext = context.SnmpContext(snmpEngine)

    # Create MIB builder
    global mibBuilder
    mibBuilder = snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder

    # Optionally set an alternative path to compiled MIBs
    print("Setting MIB sources...")
    MIBDIR = r"./pwd/mibfiles/"
    mibBuilder.addMibSources(builder.DirMibSource(MIBDIR))
    print("done")

    # Load modules
    print("Loading MIB modules...")
    mibBuilder.loadModules(model_name)

    """
    print("Indexing MIB objects..."),
    mibView = view.MibViewController(mibBuilder)
    print(mibView.getNodeName((1, 3, 6, 1, 4, 1, 8691, 2, 19, 1, 6, 4, 1, 1, 0)))
    print("done")
    """

    # Build mib tree
    print("Building MIB tree...")
    global mibInstrum
    mibInstrum = snmpContext.getMibInstrum()
    print("done")

    print("Building table entry index from human-friendly representation...")
    global portEntry
    portEntry, = mibBuilder.importSymbols(
        model_name, "portEntry"
    )
    """
    networkConnEntry, = mibBuilder.importSymbols(
        model_name, "modbusProtocolEntry"
    )
    """

    global MibScalarInstance
    MibScalarInstance, = mibBuilder.importSymbols(
        "SNMPv2-SMI", "MibScalarInstance"
    )

    global power1InputStatus, power2InputStatus
    power1InputStatus, = mibBuilder.importSymbols(
        model_name, "power1InputStatus"
    )
    power2InputStatus, = mibBuilder.importSymbols(
        model_name, "power2InputStatus"
    )
    print("done")

    """
    # Modify mibscalar value

    class Mypower1InputStatus(MibScalarInstance):
        # noinspection PyUnusedLocal
        def readGet(self, name, *args):
            # Just return a custom value
            return name, self.syntax.clone(power1InputStatus_Value.get())
    class Mypower2InputStatus(MibScalarInstance):
        # noinspection PyUnusedLocal
        def readGet(self, name, *args):
            # Just return a custom value
            return name, self.syntax.clone(power2InputStatus_Value.get())

    _power1InputStatus = Mypower1InputStatus(
        power1InputStatus.name, (0,), power1InputStatus.syntax
    )
    _power2InputStatus = Mypower2InputStatus(
        power2InputStatus.name, (0,), power2InputStatus.syntax
    )

    
    failedLoginLockedTime = MibScalarInstance(
        failedLoginLockedTime.name, (1, 3, 6, 1, 4, 1, 8691, 2, 19, 1, 6, 4, 1, 12, 0),
        failedLoginLockedTime.syntax.clone(50)
    )
    print(failedLoginLockedTime)
    

    # Register Managed Object with a MIB tree
    mibBuilder.exportSymbols(
        # "__" prefixed MIB modules take precedence on indexing
        model_name,
        _power1InputStatus=_power1InputStatus,
        _power2InputStatus=_power2InputStatus
    )
    """

    print("Getting instance ID")
    global instanceId
    instanceId = portEntry.getInstIdFromIndices(10)
    print("done")

    write_var()

    """
    # Modify mibtable value
    print("Create/update MOXA-NPS9450-MIB::consoleSetting table row: ")
    varBinds = mibInstrum.writeVars(
        ((portEntry.name + (2,) + instanceId, port_status),)
    )

    #mibInstrum.writeVars(((networkConnEntry.name + (2,) + instanceId_networkConnEntry, "0"),))
    #mibInstrum.writeVars(((realComEntry.name + (1,) + instanceId,"4"),))

    for oid, val in varBinds:
        print("%s = %s" % (".".join([str(x) for x in oid]), not val.isValue and "N/A" or val.prettyPrint()))
    print("done")

    print("Read whole MIB (table walk)")
    oid, val = (), None
    while True:
        oid, val = mibInstrum.readNextVars(((oid, val),))[0]
        if exval.endOfMib.isSameTypeWith(val):
            break
        print("%s = %s\n" % (".".join([str(x) for x in oid]), not val.isValue and "N/A" or val.prettyPrint()))
    print("done")
    """

    # Register SNMP Applications at the SNMP engine for particular SNMP context
    cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
    cmdrsp.SetCommandResponder(snmpEngine, snmpContext)
    cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
    cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

    # Register an imaginary never-ending job to keep I/O dispatcher running forever
    snmpEngine.transportDispatcher.jobStarted(1)  # this job would never finish

    global connect_first
    # Run I/O dispatcher which would receive queries and send responses
    try:
        print("here")
        connect_first = 1
        snmpEngine.transportDispatcher.runDispatcher()
    except:
        print("there")
        snmpEngine.transportDispatcher.closeDispatcher()
        raise

def write_var():
    global mibBuilder, snmpEngine, model_name, power1InputStatus, power2InputStatus, instanceId, mibInstrum, portEntry, connect_first

    class Mypower1InputStatus(MibScalarInstance):
        # noinspection PyUnusedLocal
        def readGet(self, name, *args):
            # Just return a custom value
            return name, self.syntax.clone(power1InputStatus_Value.get())

    class Mypower2InputStatus(MibScalarInstance):
        # noinspection PyUnusedLocal
        def readGet(self, name, *args):
            # Just return a custom value
            return name, self.syntax.clone(power2InputStatus_Value.get())

    _power1InputStatus = Mypower1InputStatus(
        power1InputStatus.name, (0,), power1InputStatus.syntax
    )
    _power2InputStatus = Mypower2InputStatus(
        power2InputStatus.name, (0,), power2InputStatus.syntax
    )

    # Register Managed Object with a MIB tree
    if connect_first == 0:
        mibBuilder.exportSymbols(
            # "__" prefixed MIB modules take precedence on indexing
            model_name,
            _power1InputStatus=_power1InputStatus,_power2InputStatus=_power2InputStatus)

    mibInstrum.writeVars(
        ((portEntry.name + (2,) + instanceId, portEnable_Value.get()),)
    )

def press_disconnect():
    global snmpEngine, connect_first
    connect_first = 0
    switchButtonState()
    print("disconnect")
    # finish the job
    snmpEngine.transportDispatcher.jobFinished(1)
    #th_connect.paused = True
    #exit()

def switchButtonState():
    if (connection_button["text"] == "connect"):
        connection_button.config(text = "disconnect")
        connection_button.config(command=press_disconnect)
    else:
        connection_button.config(text = "connect")
        connection_button.config(command=press_connect)

def modify_checkbutton():
    if (connection_button["text"] == "disconnect"):
        write_var()

# Main thread
print("START!!!")
global connect_first
connect_first = 0

# 例項化object，建立視窗window
window = tk.Tk()

# 給視窗的視覺化起名字
window.title("virtual nport")

# 設定視窗的大小(長 * 寬)
window.geometry("500x400")  # 這裡的乘是小x
window.resizable(width = 0, height = 0)

# 在圖形介面上設定標籤
model = tk.Label(window, text = "MODEL", font = ("Arial", 10))
ip = tk.Label(window, text = "IP", font = ("Arial", 10))
port = tk.Label(window, text = "PORT", font = ("Arial", 10))
# 說明： bg為背景，font為字型，width為長，height為高，這裡的長和高是字元的長和高，比如height=2,就是標籤有2個字元這麼高

# 放置標籤
model.place(x = 30,y = 30)    # Label內容content區域放置位置，自動調節尺寸
ip.place(x = 30,y = 70)
port.place(x = 200,y = 70)
# 放置lable的方法有：1）model.pack(); 2)model.place();

# 輸入欄位
ip_entry = tk.Entry(window,     # 輸入欄位所在視窗
              width = 15,       # 輸入欄位的寬度
)
ip_entry.place(x = 60,y = 70)

port_entry = tk.Entry(window,
              width = 5,
)
port_entry.place(x = 255,y = 70)

# 放置checkbutton
portEnable_Value = tk.BooleanVar()
portEnable_Value.set(False)

portEnable_Example = tk.Checkbutton(window, text = "portEnable", variable = portEnable_Value, onvalue = 1, offvalue = 0, command = modify_checkbutton)
portEnable_Example.place(x = 30, y = 100)

power1InputStatus_Value = tk.BooleanVar()
power1InputStatus_Value.set(False)

power1InputStatus_Example = tk.Checkbutton(window, text = "power1InputStatus", variable = power1InputStatus_Value, onvalue = 1, offvalue = 0, command = modify_checkbutton)
power1InputStatus_Example.place(x = 30, y = 130)

power2InputStatus_Value = tk.BooleanVar()
power2InputStatus_Value.set(False)

power2InputStatus_Example = tk.Checkbutton(window, text = "power2InputStatus", variable = power2InputStatus_Value, onvalue = 1, offvalue = 0, command = modify_checkbutton)
power2InputStatus_Example.place(x = 170, y = 130)

# 放置button
connection_button = tk.Button(window, text = "connect", fg = "black", command=press_connect)
connection_button.place(x = 220, y = 300)

# 放置下拉選單
model_combo = ttk.Combobox(window, values = ["MOXA-NPS9450"])
model_combo.place(x = 90, y = 30)

# 主視窗迴圈顯示
window.mainloop()
# 注意，loop因為是迴圈的意思，window.mainloop就會讓window不斷的重新整理，如果沒有mainloop,就是一個靜態的window,傳入進去的值就不會有迴圈，mainloop就相當於一個很大的while迴圈，有個while，每點選一次就會更新一次，所以我們必須要有迴圈
# 所有的視窗檔案都必須有類似的mainloop函式，mainloop是視窗檔案的關鍵的關鍵。

