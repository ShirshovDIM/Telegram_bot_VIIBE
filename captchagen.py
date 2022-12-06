from captcha.image import ImageCaptcha
import random

def captcha_gen():
    alpha = ['0','1','2','3','4','5','6','7','8','9']
    rnd_num = ''.join(random.choices(alpha, k= 6))
    captcha = ImageCaptcha(width= 280, height= 90)
    captcha.write(rnd_num, 'captcha.png')
    return rnd_num

