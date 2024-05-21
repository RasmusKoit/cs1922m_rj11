import network
import time
from machine import Pin, SoftI2C, UART, Timer, reset
import ssd1306
import secrets

# Constants
BUTTON_ONE_PIN = 0
BUTTON_TWO_PIN = 1
LED_PIN = "LED"
I2C_SCL_PIN = 3
I2C_SDA_PIN = 2
UART_TX_PIN = 4
UART_RX_PIN = 5

WIFI_SSID = secrets.WIFI_SSID
WIFI_PASSWORD = secrets.WIFI_PASSWORD
WIFI_TIMEOUT = 30  # Timeout for WiFi connection in seconds

DEBOUNCE_TIME_MS = 1000
DISPLAY_DURATION = 5

# Initialize hardware
BUTTON_ONE = Pin(BUTTON_ONE_PIN, Pin.IN, Pin.PULL_UP)
BUTTON_TWO = Pin(BUTTON_TWO_PIN, Pin.IN, Pin.PULL_UP)
LED = Pin(LED_PIN, Pin.OUT)
timer = Timer()

# Global variables
buttonPressed = False
buttonMessage = ""
buttonPressTime = 0
selectedKVM = 1
lastPressTime = {BUTTON_ONE: 0, BUTTON_TWO: 0}
startTime = 0
lastButtonPressed = BUTTON_ONE
oled = None
uart = None
wlan = network.WLAN(network.STA_IF)

def blinkLED(timer):
    LED.toggle()

def connectToWifi():
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > WIFI_TIMEOUT:
            print("Failed to connect to WiFi")
            return False
        print('Waiting for connection...')
        time.sleep(1)
    
    print("Connected to WiFi", wlan.ifconfig())
    timer.deinit()
    return True

def openKVM():
    print('Open')
    uart.write('open\r\n')
    time.sleep(1)

def closeKVM():
    print('Close')
    uart.write('close\r\n')
    time.sleep(1)

def switchKVM(kvmPort):
    message = f'Switching to port {kvmPort}'
    print(message)
    uart.write(f'sw i0{kvmPort}\r\n')
    time.sleep(2)

def updateDisplay(uptimeSeconds):
    try:
        global buttonPressed
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
        oled.text(f"KVM Port: {selectedKVM}", 38, 20, 1)
        oled.hline(36, 48, 128, 1)
        oled.vline(36, 16, 32, 1)
        oled.vline(127, 16, 32, 1)

        if buttonPressed and (time.time() - buttonPressTime) < DISPLAY_DURATION:
            oled.text(buttonMessage, 0, 54, 1)
        else:
            oled.text("", 0, 54, 1)
            buttonPressed = False
        oled.show()
    except Exception as e:
        print(f'Display update failed: {e}')

def handleButton(pin):
    global buttonPressed, buttonMessage, buttonPressTime, selectedKVM, lastPressTime, startTime, lastButtonPressed
    currentTime = time.time()
    if time.ticks_diff(currentTime, lastPressTime[pin]) < DEBOUNCE_TIME_MS:
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
    buttonPressTime = currentTime
    lastButtonPressed = pin
    updateDisplay(currentTime - startTime)
    openKVM()
    switchKVM(str(selectedKVM))
    closeKVM()

def initialize_display():
    global oled
    try:
        print('Initializing display...')
        time.sleep(5)
        I2C = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
        time.sleep(5)
        while I2C.scan() == []:
            print('I2C device not found')
            time.sleep(1)
        oled = ssd1306.SSD1306_I2C(128, 64, I2C)
        time.sleep(1)  # Additional delay to stabilize the display
        print('Display initialized')
    except Exception as e:
        print(f'Display initialization failed: {e}')
        time.sleep(10)
        # reset()  # Reset the Pico if the display initialization fails

def initialize_uart():
    global uart
    try:
        uart = UART(1, baudrate=19200, bits=8, parity=None, stop=1, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))
        print('UART initialized')
    except Exception as e:
        print(f'UART initialization failed: {e}')

def cleanup():
    wlan.active(False)
    wlan.disconnect()
    if oled:
        oled.fill(0)
        oled.show()
    print('Goodbye!')

# Main execution
try:
    time.sleep(1)
    timer.init(period=500, mode=Timer.PERIODIC, callback=blinkLED)
    
    connectToWifi()
    initialize_uart()
    initialize_display()

    BUTTON_ONE.irq(trigger=Pin.IRQ_FALLING, handler=lambda pin: handleButton(pin))
    BUTTON_TWO.irq(trigger=Pin.IRQ_FALLING, handler=lambda pin: handleButton(pin))

    startTime = time.time()

    while True:
        currentTime = time.time()
        uptimeSeconds = int(currentTime - startTime)
        updateDisplay(uptimeSeconds)
        time.sleep(1)

except Exception as e:
    print(f'Error: {e}')
except KeyboardInterrupt:
    print('Ctrl+C: Exiting...')
finally:
    cleanup()
