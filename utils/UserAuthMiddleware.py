from datetime import datetime

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from backweb.models import UserTicket, Cart


class AuthMiddleWare(MiddlewareMixin):

    def process_request(self,request):
        path = request.path
        # 在不登录时放过
        list = ['/app/index/', '/app/detail/', '/app/addcart/','/app/cart/','/app/alter_cart_goods/', '/app/del_shop_car/', '/app/alter_cart_select/', '/app/money/', '/app/cartnum/', '/app/check_all/','/app/goodsall/', '/app/alter_cart_select/', '/app/good_money/', '/app/list/']
        # 放过
        on_list = ['/app/login/', '/app/register/', '/backweb/login/' ]
        # 放过图片
        if '/media/' in path:
            return None
        if path in on_list:
            return None
        ticket = request.COOKIES.get('ticket')

        userticket = UserTicket.objects.filter(ticket=ticket).first()
        if 'backweb' in path and userticket:
            if userticket.user.is_admin != '1':
                 return HttpResponseRedirect(reverse('backweb:login'))
        if userticket:
            if userticket.out_time.replace(tzinfo=None) > datetime.now():
                request.user = userticket.user
            else :
                userticket.delete()
                return HttpResponseRedirect(reverse('app:login'))
        elif path in list:
            return None
        else:
            return HttpResponseRedirect(reverse('app:login'))


class AuthSessionMiddleware(MiddlewareMixin):
    pass

    def process_request(self, request):
        # 获得session中的状态判断是否同步到数据库
        if request.session.get('login_status'):
            # 检测到有用户登录，从cookie中找到该用户
            user = request.user
            # 如果用户存在(user.model)
            if user.id:
                # 获得session中存储的购物数据
                goods = request.session.get('goods')
                # 如果存在购物数据将其同步到购物车数据库中
                if goods:
                    # 循环将session数据加到购物车
                    for good in goods:
                        # 判断该物品是否存在购物车，存在就改变购物车数量，不存在就添加新的购物车数据
                        cart = Cart.objects.filter(goods_id=good[0], user=user).first()
                        if not cart:
                            # 没有相同的购物物品，创建新的数据
                            Cart.objects.create(goods_id=good[0], c_num=good[1], is_select=good[2], user=user)
                        else:
                            # 存在相同购物数据，增加物品数量
                            cart.c_num = cart.c_num + int(good[1])
                            cart.is_select = good[2]
                            cart.save()
                    # 将数据写回session中
                    request.session['goods'] = []

        return None























