from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (900, 200), "white")
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("arial.ttf", 48)
draw.text((30, 70), "book dentist nxt Friday @ 3 pm", fill="black", font=font)
img.save("sample.png")