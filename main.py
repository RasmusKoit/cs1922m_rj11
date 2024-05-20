import network
import time
from machine import Pin, SoftI2C, UART, reset, Timer
import ssd1306 # type: ignore
import secrets


BUTTON_ONE = Pin(0, Pin.IN, Pin.PULL_UP)
BUTTON_TWO = Pin(1, Pin.IN, Pin.PULL_UP)

LED = Pin("LED", Pin.OUT)
timer = Timer()

def blinkLED(timer):
    LED.toggle()

timer.init(period=500, mode=Timer.PERIODIC, callback=blinkLED)

time.sleep(8)
I2C = SoftI2C(scl=Pin(3), sda=Pin(2))
time.sleep(5)
oled = ssd1306.SSD1306_I2C(128, 64, I2C)
time.sleep(1)
oled.rotate(True)
uart = UART(1, baudrate=19200, bits=8, parity=None, stop=1, tx=Pin(4), rx=Pin(5))
wlan = network.WLAN(network.STA_IF)

buttonPressed = False
buttonMessage = ""
displayDuration = 5
buttonPressTime = 0
selectedKVM = 1
lastPressTime = {BUTTON_ONE: 0, BUTTON_TWO: 0}
debounceTimeMs = 2000
startTime = 0
lastButtonPressed = BUTTON_ONE



def connectToWifi():
    #Connect to WLAN
    wlan.active(True)
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        time.sleep(1)
    print("Connected to WiFi", wlan.ifconfig())
    time.sleep(1)
    timer.deinit()

def openKVM():
    print('Open')
    uart.write('open\r\n')
    time.sleep(1)

def closeKVM():
    print('Close')
    uart.write('close\r\n')
    time.sleep(1)

def switchKVM(kvmPort):
    message = 'Switching to port ' + kvmPort
    print(message)
    uart.write('sw i0' + kvmPort + '\r\n')
    time.sleep(2)

def updateDisplay(uptimeSeconds):
    center_x, center_y = 16, 33
    oled.fill(0)
    uptimeMessage = 'Uptime: {:02d}:{:02d}:{:02d}'.format(uptimeSeconds // 3600, (uptimeSeconds % 3600 // 60), uptimeSeconds % 60)
    oled.text(uptimeMessage, 0, 0, 1)
    oled.hline(36, 16, 128, 1)
    for x in range(64):
        for y in range(64):
            if (x - center_x) ** 2 + (y - center_y) ** 2 >= 15 ** 2 and (x - center_x) ** 2 + (y - center_y) ** 2 <= (15 + 2) ** 2:
                oled.pixel(x, y, 1)
    oled.text('KVM', center_x - 12, center_y - 4, 1)
    oled.text('CS1922M KVM', 38, center_y + 2, 1)
    oled.text("KVM Port: {}".format(selectedKVM), 38, 20, 1)
    # Draw a line under the logo and text
    oled.hline(36, 48, 128, 1)
    oled.vline(36, 16, 32, 1)
    oled.vline(127, 16, 32, 1)

    if buttonPressed and (time.time() - buttonPressTime) < displayDuration:
        oled.text(buttonMessage, 0, 54, 1)  # Display button message on the second line
    else:
        oled.text("", 0, 54, 1)
    oled.show()

def handleButton(pin):
    global buttonPressed, buttonMessage, buttonPressTime, selectedKVM, lastPressTime, startTime, lastButtonPressed
    currentTime = time.time()
    if time.ticks_diff(currentTime, lastPressTime[pin]) < debounceTimeMs:
        return
    
    if lastButtonPressed != pin:
        startTime = time.time()
    if pin == BUTTON_ONE:
        buttonMessage = "Button 1 pressed"
        selectedKVM = 1
    elif pin == BUTTON_TWO:
        buttonMessage = "Button 2 pressed"
        selectedKVM = 2
    lastPressTime[pin] = currentTime
    buttonPressed = True
    buttonPressTime = time.time()
    lastButtonPressed = pin
    updateDisplay(currentTime - startTime)
    openKVM()
    switchKVM(str(selectedKVM))
    closeKVM()

# Wait for bootup
try:
    time.sleep(1)
    # connectToWifi()
    
    BUTTON_ONE.irq(trigger=Pin.IRQ_FALLING, handler=lambda pin: handleButton(pin))
    BUTTON_TWO.irq(trigger=Pin.IRQ_FALLING, handler=lambda pin: handleButton(pin))

    startTime = time.time()

    while True:
        currentTime = time.time()
        uptimeSeconds = int(currentTime - startTime)
        updateDisplay(uptimeSeconds)
        time.sleep(1)
except:
    print('Exiting...')
    wlan.active(False)
    wlan.disconnect()
    oled.fill(0)
    oled.show()
    time.sleep(1)
    print('Goodbye!')
