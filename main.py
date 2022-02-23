import time
import cv2 as cv
from kivy.clock import Clock
from kivy.core.image import Texture
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import threading
import queue
from datetime import datetime
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.image import Image
from pyzbar.pyzbar import decode

RED_COLOR = (0.5, 0.1, 0, 1)
GREEN_COLOR = (0.3, 0.7, 0.2, 1)
YELLOW_COLOR = (1, 0.9, 0.1, 1)


def mytime():
    now = datetime.now()
    return now.strftime("%H:%M:%S")


class CameraStream(Image):
    last_decoded = StringProperty()
    play = True

    def get_barcode(self):
        return self.last_decoded
        self.last_decoded = ''

    def on_kv_post(self, base_widget):
        self.capture = cv.VideoCapture(0, cv.CAP_DSHOW)

        if self.play:
            Clock.schedule_interval(self.update, 1.0 / 33.0)

    def update(self, dt):

        ret, frame = self.capture.read()
        if ret is False:
            print("no frame")
        else:
            width, height, _ = frame.shape
            buf1 = cv.flip(frame, 0)
            buf = buf1.tobytes()
            texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')  # replacing texture
            self.texture = texture1

            #Barcode parsen
            #Data Sample [Decoded(data=b'4334011217192', type='EAN13', rect=Rect(left=290, top=146, width=108, height=218), polygon=[Point(x=290, y=256), Point(x]
            img_decoded = decode(frame)
            if img_decoded:
                barcode = img_decoded[0].data.decode()
                if barcode != self.last_decoded:
                    #print(barcode)
                    self.last_decoded = barcode


class WebSeller(Widget):
    camera = ObjectProperty()
    txtpreisrebuy = StringProperty()
    txtpreismomox = StringProperty()
    txtpreisdeinecds = StringProperty()

    time = StringProperty()
    txtbarcode = StringProperty()

    site_list = ["https://www.momox.de", "https://www.verkauf-deine-cds.de/ankauf/", "https://www.rebuy.de/verkaufen"]
    site_name = ["momox", "deinecds", "rebuy"]
    ean_queue_in = []
    ean_queue_out = []
    qnr_color = []
    threads = []

    def SimpleClock(self, dt):
        self.time = mytime()
        return

    def multi_browser(self, website, name, qnr, qnr_out, qnr_color):
        options = Options()
        options.headless = True

        if name == "deinecds":
            service = Service("gecko_zoxs.exe")
        elif name == "momox":
            service = Service("gecko_momox.exe")
        elif name == "rebuy":
            service = Service('gecko_rebuy.exe')

        print("Browser start loading" + website + " " + mytime())
        driver = Firefox(service=service, options=options)

        qnr_color.put(name)

        print("Browser " + website + " loaded " + mytime())

        count = 1

        while True:
            if not qnr.empty():
                barcode = qnr.get()

                if name == 'momox':
                    self.txtpreismomox = ''
                    driver.get(website)
                    if count == 1:
                        driver.find_element(By.XPATH, '//*[text()="Alle akzeptieren"]').click()
                        count = 0
                    driver.find_element(By.CLASS_NAME, 'searchbox-input').send_keys(barcode)
                    driver.find_element(By.XPATH, '//*[@id="buttonMediaSearchSubmit"]').click()
                    try:
                        time.sleep(1)
                        pricetag = driver.find_element(By.CLASS_NAME, 'searchresult-price').text

                    except NoSuchElementException:
                        pricetag = "0.00 €"


                elif name == 'rebuy':
                    self.txtpreisrebuy = ''
                    driver.get(website)
                    driver.find_element(By.XPATH,
                                        '/html/body/main/div[1]/div[1]/div[2]/div/div/div[1]/form/div/input[1]').send_keys(
                        barcode)
                    driver.find_element(By.XPATH,
                                        '/html/body/main/div[1]/div[1]/div[2]/div/div/div[1]/form/div/button').click()
                    try:
                        time.sleep(1)
                        pricetag = driver.find_element(By.CLASS_NAME, 'product-price').text
                    except NoSuchElementException:
                        pricetag = "0.00 €"


                elif name == 'deinecds':
                    self.txtpreisdeinecds = ''
                    driver.get(website)
                    driver.find_element(By.ID, 'scan_barcode').send_keys(barcode)
                    driver.find_element(By.CLASS_NAME, 'form_input_submit_big').click()
                    try:
                        pricetag = driver.find_element(By.CLASS_NAME, 'artikel_price').text
                    except NoSuchElementException:
                        pricetag = "0,00 €"

                print("Website:" + website + " Barcode:" + barcode + " Preis:" + pricetag + " Timestamp:" + mytime())

                qnr_out.put(pricetag)
            else:
                time.sleep(0.1)
                pass

    def browserthreads(self):
        print("Programm started " + mytime())

        for count, site in enumerate(self.site_list):
            t = threading.Thread(target=self.multi_browser, args=(
                site, self.site_name[count], self.ean_queue_in[count], self.ean_queue_out[count],
                self.qnr_color[count]))
            self.threads.append(t)

        for t in self.threads:
            t.start()

    def set_focus(self):
        self.ids.barcode_input.focus = True

    def AddBarcodeToQueue(self):
        print("Callback" + mytime())

        for e in self.ean_queue_in:
            if e.empty():
                e.put(self.ids.barcode_input.text)

    def CheckBrowserLoaded(self, dt):
        new_barcode = self.camera.get_barcode()
        if new_barcode:
            self.ids.barcode_input.text = new_barcode
            self.ids.barcode_input.focus = True
        #else:
       #     self.ids.barcode_input.text = ''
        #    self.ids.barcode_input.focus = False

        for count, i in enumerate(self.qnr_color):
            if not i.empty():
                browser = i.get()
                if browser == "deinecds":
                    self.colorbrowserdeinecds = GREEN_COLOR
                elif browser == "momox":
                    self.colorbrowsermomox = GREEN_COLOR
                elif browser == "rebuy":
                    self.colorbrowserrebuy = GREEN_COLOR

    def check_return_queue(self, dt):
        count = 0
        for i in self.ean_queue_out:
            if not i.empty():
                count += 1
        if count == 3:
            self.txtpreismomox = self.ean_queue_out[0].get()
            self.txtpreisdeinecds = self.ean_queue_out[1].get()
            self.txtpreisrebuy = self.ean_queue_out[2].get()

    def barcode_queues(self):
        for site in enumerate(self.site_list):
            i = queue.Queue(maxsize=1)
            self.ean_queue_in.append(i)

            o = queue.Queue(maxsize=1)
            self.ean_queue_out.append(o)

            x = queue.Queue(maxsize=1)
            self.qnr_color.append(x)


class WebSellerApp(App):
    def build(self):
        webseller = WebSeller()
        webseller.barcode_queues()
        webseller.browserthreads()
        Clock.schedule_interval(webseller.CheckBrowserLoaded, 1)
        Clock.schedule_interval(webseller.SimpleClock, 1)
        Clock.schedule_interval(webseller.check_return_queue, 1)
        return webseller


if __name__ == '__main__':
    WebSellerApp().run()
    print('Execution completed')
