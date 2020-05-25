import os
import random
from PIL import Image, ImageDraw, ImageColor, ImageFilter, ImageOps

WIDTH = 240
HEIGHT = 160
SIZE = WIDTH, HEIGHT

def dark(rand):
    '''a random dark color'''
    hue = rand.randrange(360)
    saturation = rand.randrange(90)
    lightness = rand.randrange(10,40)
    return ImageColor.getrgb(f'hsl({hue}, {saturation}%, {lightness}%)')

def light(rand):
    '''a random light color'''
    hue = rand.randrange(360)
    saturation = rand.randrange(90)
    lightness = rand.randrange(60,90)
    return ImageColor.getrgb(f'hsl({hue}, {saturation}%, {lightness}%)')

def skin(rand):
    '''a random skin color'''
    hue = rand.randrange(360)
    saturation = rand.randrange(30,50)
    lightness = rand.randrange(30,70)
    return ImageColor.getrgb(f'hsl({hue}, {saturation}%, {lightness}%)')

def cloth(rand):
    '''a random cloth color'''
    hue = rand.randrange(360)
    saturation = rand.randrange(70,100)
    lightness = rand.randrange(10,90)
    return ImageColor.getrgb(f'hsl({hue}, {saturation}%, {lightness}%)')

def background(rand):
    y = rand.randrange(HEIGHT // 6, 5 * (HEIGHT // 6))
    if rand.random() < 0.5:
        top = dark(rand)
        bottom = light(rand)
    else:
        top = light(rand)
        bottom = dark(rand)
    img = Image.new('RGB', SIZE, bottom)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0,0,WIDTH,y), fill=top, width=0)
    img.filter(ImageFilter.BLUR)
    return img

def add_colorized_layer(img, layer, color):
    colorized = ImageOps.colorize(layer.convert('L'), black=color, white='white')
    print(img.size, layer.size, colorized.size)
    return Image.composite(img, colorized, layer)

def body(rand, img):
    fname = os.path.join('randimage', 'body.png')
    return add_colorized_layer(img, Image.open(fname), cloth(rand))

def pants(rand, img):
    fnames = ['pant1.png', 'pant2.png', 'pant3.png']
    fname = os.path.join('randimage', rand.choice(fnames))
    return add_colorized_layer(img, Image.open(fname), cloth(rand))

def shirt(rand, img):
    fnames = ['shirt1.png', 'shirt2.png', 'shirt3.png']
    fname = os.path.join('randimage', rand.choice(fnames))
    return add_colorized_layer(img, Image.open(fname), cloth(rand))

def randimage(seed):
    rand = random.Random()
    rand.seed(seed)
    img = background(rand)
    img = body(rand, img)
    img = pants(rand, img)
    img = shirt(rand, img)
    return img

if __name__ == '__main__':
    import random
    rand = random.Random()
    img = randimage(random.random())
    img.show()
