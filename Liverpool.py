import pyautogui
import pygetwindow as gw
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import time

def capture_screenshot(window, region, filename):
    # Activate the window
    window.activate()
    time.sleep(1)  # Give some time to the window to activate

    # Capture screenshot of the region
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(filename)

def main():
    # Create a new Excel workbook and select the active sheet
    wb = Workbook()
    ws = wb.active

    # Add headers to the Excel sheet
    ws.append(["Window Title", "Screenshot"])

    # Define the region to capture (left, top, width, height)
    region = (0, 0, 800, 600)  # Adjust this to your desired region

    # Iterate through all the open windows
    for window in gw.getWindowsWithTitle(''):
        if window.title:  # Only consider windows with a title
            # Capture screenshot and save to a file
            screenshot_filename = f"{window.title}.png"
            capture_screenshot(window, region, screenshot_filename)

            # Append the window title and screenshot filename to the Excel sheet
            ws.append([window.title])

            # Add the image to the Excel sheet
            img = Image(screenshot_filename)
            img.anchor = f'B{ws.max_row}'
            ws.add_image(img)

    # Save the workbook
    wb.save("windows_screenshots.xlsx")

if __name__ == "__main__":
    main()
