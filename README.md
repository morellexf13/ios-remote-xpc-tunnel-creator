<div align="center">
  <h1>
    <br/>
    🚇
    <br />
    <br />
    RemoteXPC Tunnel Creator
    <br />
    <br />
  </h1>
  <sup>
    <br />
   Create a rooted binary to communicate a computer with an iOS 17 device to use developer services.</em>
    <br />
    <br />

[![License](https://img.shields.io/badge/-MIT-red.svg?longCache=true&style=for-the-badge)](https://github.com/morellexf13/boilersnake/blob/main/LICENSE)

  </sup>
</div>

<br>

### 🙋🏼Why?

Starting at iOS 17.0, Apple refactored a lot in the way iOS devices communicate with the macOS. Up until iOS 16, The communication was TCP based (using the help of usbmuxd for USB devices) with TLS (for making sure only trusted peers are able to connect). You can read more about the old protocol in this article:

https://jon-gabilondo-angulo-7635.medium.com/understanding-usbmux-and-the-ios-lockdown-service-7f2a1dfd07ae

The new protocol stack relies on QUIC+RemoteXPC which should reduce much of the communication overhead in general - allowing faster and more stable connections, especially over WiFi.

### ⚠️ Pre-requisites

Python 3

Install requirements

```
pip3 install -r requirements.txt
```

### 🦺 Build

1- Create binary with ```pyinstaller main.py --name remote-xpc-tunnel```

2- Give root permissions (needed) [pymobiledevice3 issues#562](https://github.com/doronz88/pymobiledevice3/issues/562#issuecomment-1724226316)

```
cd dist/remote-xpc-tunnel
sudo chown root ./remote-xpc-tunnel
sudo chmod u+s ./remote-xpc-tunnel
```

### 🏃🏽‍♂️ Run

```sudo ./remote-xpc-tunnel --udid ABCDEF12-34567890ABCDEF12```
