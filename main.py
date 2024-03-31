import tkinter as tk
import tkinter.font as font
from tkinter import ANCHOR, ttk

import nfc

import felica

FELICA_HISPEED = False

# メインウィンドウの生成
root = tk.Tk()
root.geometry("1280x720")
root.title("Treeview")

rootfont = font.Font(root, family="Cascadia Code", size=12)

style = ttk.Style()
style.configure("Treeview", font=rootfont)

cardDetail = tk.Label(root, text="Felica", anchor=tk.W, font=rootfont)
cardDetail.pack(padx=5, pady=5, fill=tk.X)

paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
paned_window.pack(fill=tk.BOTH, expand=True)

card_tree = ttk.Treeview(paned_window, show=["tree"])
paned_window.add(card_tree, weight=1)

data_view = ttk.Treeview(paned_window, columns=("Block", "Data", "ASCII"), show=["headings"])
paned_window.add(data_view, weight=1)


data_view.column("Block", width=30, stretch=False, anchor=tk.E)
data_view.column("ASCII", width=200, stretch=False, anchor=tk.W)

data_view.heading("Block", text="")
data_view.heading("Data", text="Data", anchor=tk.W)
data_view.heading("ASCII", text="ASCII view", anchor=tk.W)

### nfcpy
clf = nfc.ContactlessFrontend("usb")

if FELICA_HISPEED:
    target = nfc.clf.RemoteTarget("424F")
else:
    target = nfc.clf.RemoteTarget("212F")


target.sensf_req = bytearray.fromhex("00 ffff 01 0f")  # type:ignore


print("Waiting card...")
sense = None
while sense is None:
    sense = clf.sense(target)

print("target: ", str(sense))


idm: bytes = sense.sensf_res[1 : 1 + 8]
pmm: bytes = sense.sensf_res[9 : 9 + 8]
request_data: bytes = sense.sensf_res[9 + 8 : 9 + 10]

print(f"IDm={idm.hex()} PMm={pmm.hex()} RequestData={request_data.hex()}")

cardDetail["text"] = f"{felica.get_ic_type(pmm[1])} IDm={idm.hex()} PMm={pmm.hex()}"

isLiteS = False

if int.from_bytes(request_data) == 0x88B4:
    isLiteS = True
    system_tree = card_tree.insert("", "end", text=f"System {request_data.hex()}", open=True)

    child = card_tree.insert(system_tree, "end", text=f"Service {0x008b:04x}", open=True)

    serviceDict = {}

    temp = []

    for i in felica.liteSBlockList:
        # Felica Lite-S

        SF1, SF2, data = felica.readWoEnc(clf, idm, b"\x00\x0b", i)

        if SF2 == 0xB1 and data is None:
            temp.append(None)
            pass
        else:
            temp.append(data)
            pass

    serviceDict[child] = {"serviceCode": b"\x00\x0b", "data": temp}
else:
    # Felica Standard
    systemCode: list[bytearray] = felica.requestSystemCode(clf, idm)

    serviceDict = {}
    for i in systemCode:

        system_tree = card_tree.insert("", "end", text=f"System {i.hex()}", open=True)

        idm, pmm, _ = felica.polling(clf, i)

        treeList = [system_tree]
        lastSvCList = [0xFFFF]

        temp_counter = 0
        while True:
            serviceCode, areaCode, endServiceCode = felica.searchServiceCode(clf, idm, temp_counter)

            if serviceCode is not None and serviceCode[0] == 0xFF and serviceCode[1] == 0xFF:
                break

            if areaCode is not None and endServiceCode is not None:
                counter = len(lastSvCList) - 1
                while True:
                    if lastSvCList[counter] >= int.from_bytes(endServiceCode):
                        break
                    counter -= 1

                child = card_tree.insert(
                    treeList[counter], "end", text=f"Area {areaCode.hex()}-{endServiceCode.hex()}", open=True
                )
                lastSvCList.append(int.from_bytes(endServiceCode))
                treeList.append(child)

                pass
            elif serviceCode is not None:
                serviceCodeInt = int.from_bytes(serviceCode)
                service, access, withEnc = felica.parse_service_code(serviceCode)

                service_tree = card_tree.insert(
                    treeList[-1],
                    "end",
                    text=f"{felica.service_to_str(service)}service {(serviceCodeInt & 0xFFC0) >> 6} {felica.access_to_str(access, withEnc)}: 0x{serviceCode.hex()}",
                )

                block_data = None
                if withEnc == False:
                    block_data = felica.readWoEncOneService(clf, idm, serviceCode)

                serviceDict[service_tree] = {"serviceCode": serviceCode, "data": block_data}

                print(block_data)

            temp_counter += 1

dataViewItemList = []


def tree_clicked(a):
    try:
        data = serviceDict[card_tree.focus()]["data"]

        # all delete
        for p in dataViewItemList:
            data_view.delete(p)

        dataViewItemList.clear()

        if data:
            for index, element in enumerate(data):
                if element:
                    dataViewItem = data_view.insert(
                        parent="",
                        index="end",
                        values=(
                            f"{felica.liteSBlockList[index]:x}" if isLiteS else f"{index:x}",
                            element.hex(" "),
                            felica.conv_bytes_to_str(element),
                        ),
                    )

                    dataViewItemList.append(dataViewItem)
                else:
                    dataViewItem = data_view.insert(
                        parent="",
                        index="end",
                        values=(
                            f"{felica.liteSBlockList[index]:x}",
                            "This block is required MAC Authenticate",
                            "",
                        ),
                    )

                    dataViewItemList.append(dataViewItem)
        else:
            dataViewItem = data_view.insert(
                parent="", index="end", values=("", "This service is required Authenticate", "")
            )

            dataViewItemList.append(dataViewItem)
            return
    except KeyError:
        return


card_tree.bind("<<TreeviewSelect>>", tree_clicked)  # type:ignore


# # 見出しの設定
# # 親要素の挿入
# parent = tree.insert("", "end", text="System 0003", open=True)
# # 子要素の挿入
# child = tree.insert(parent, "end", text="Area 0000-FFFE", open=True)


# child2 = tree.insert(child, "end", text="Area 0040-07FF", open=True)
# child3 = tree.insert(child2, "end", text="Random Service 1 r/w with key: 0x0048")
# child3 = tree.insert(child2, "end", text="Random Service 1 read with key: 0x004a")
# child3 = tree.insert(child2, "end", text="Random Service 2 r/w with key: 0x0088")
# child3 = tree.insert(child2, "end", text="Random Service 2 read w/o key: 0x008b")

# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))
# data.insert(parent="", index="end", values=(1, "00 " * 16))


root.mainloop()
