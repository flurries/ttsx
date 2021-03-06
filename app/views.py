from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from backweb.models import User, UserTicket, Goods, Cart, Order, OrderGoods, Adderss, User_visit, CarouselImg, Goodclass
from utils.functiom import get_ticket, get_order, miss_tel

# 注册
@csrf_exempt
def register(request):
    if request.method == 'GET':
        return render(request, 'app/login/register.html')
    if request.method == 'POST':
        # 获得注册用户名、密码、确认密码、邮箱
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        # 验证信息输入完整
        if not all([username, password1, password2, email]):
            data = {'error': '信息不完整'}
            return render(request, 'app/login/register.html', data)
        # 使用用户名去数据库那同名的用户
        user = User.objects.filter(username=username).exists()
        # 如果存在同名用户则重新注册
        if user:
            data = {'error': '用户名已存在'}
            return render(request, 'app/login/register.html', data)
        # 用户名没有被注册过验证两次密码是否一致
        if password2!=password1:
            data = {'error': '两次密码不一致'}
            return render(request, 'app/login/register.html', data)
        # 通过全部验证可以常见账号
        User.objects.create(username=username, password=make_password(password1), email=email)
        return render(request, 'app/login/login.html')


# 登录
def login(request):
    if request.method == 'GET':
        # 拿出之前在cookie中存储的名字做记住用户名
        name = request.COOKIES.get('name')
        # 如果没有用户名就制空
        if name is None:
            name = ''
        return render(request, 'app/login/login.html', {'name': name})
    if request.method == 'POST':
        # 拿到登录名与密码
        username = request.POST.get('username')
        password = request.POST.get('password')
        # 判断输入信息是否完整
        if not all([username, password]):
            error = '请填完所有信息'
            return render(request, 'app/index.html', {'error': error})
        # 拿到数据库对应用户
        user = User.objects.filter(username=username).first()
        # 没有用户
        if not user:
            data = {'error': '用户名不存在'}
            return render(request, 'app/index.html', data)
        # 有用户
        else:
            # 判断密码是否与数据库一致
            if check_password(password, user.password):
                # 定义重定向去主页
                res = HttpResponseRedirect(reverse('app:index'))
                # 将session中的登录状态写为True
                request.session['login_status'] = True
                # 获得现在的时间并加上24小时(一天)
                out_time =datetime.now() + timedelta(days=1)
                # 拿到之前用户提交的登录名
                name = username
                # 创建名字在在cookie中从存储时间为7天
                time = datetime.now() + timedelta(days=7)
                # 将用户之前提交的登录名写到cookie中
                res.set_cookie('name', name, expires=time)
                # 创建一个随机值用来保存在cookie与数据库中验证用户身份，
                # 在用户退出时删除cookie中的该值与数据库的对应值
                # get_ticket是utils工具里的随机函数方法
                ticket = get_ticket()
                # 获得现在的时间并加上24小时(一天)
                out_time = datetime.now() + timedelta(days=1)
                # 将随机数写进cookie中设定过期时间
                res.set_cookie('ticket', ticket, expires=out_time)
                # 在存储输数(验证用户在线上)的数据库中找用户的随机数
                userticket = UserTicket.objects.filter(user=user)
                # 如果不存在随机数，就在该数据库中添加该数据
                if not userticket:
                    UserTicket.objects.create(user=user, ticket=ticket, out_time=out_time).save()
                # 存在该数据，说明说明用户在重复登录，将这个随机数覆盖保存
                else:
                    userticket = userticket.first()
                    userticket.ticket = ticket
                    userticket.out_time = out_time
                    userticket.save()
                return res
            # 密码不一致返回login页面
            else:
                return HttpResponseRedirect(reverse('app:login'))


# 退出
def logout(request):
    if request.method == 'GET':
        # 删除数据库中存储的该用户的验证随机值
        UserTicket.objects.get(user=request.user).delete()
        # 设定重定向
        res = HttpResponseRedirect(reverse('app:index'))
        # 清除在cookie中的随机值
        res.delete_cookie('ticket')
        request.session['login_status'] = False
        return res


# 主页
def index(request):
    if request.method == 'GET':
        # 判断用户是否在线(中间件里判断用户在线并包用户信息写到request中)
        user =request.user
        # 如果存在用户ID
        if user.id:
            i = len(Cart.objects.filter(user=user))
        else:
            i = len(request.session.get('goods'))
        # 获得主页的轮播图
        img = CarouselImg.objects.all()
        # 创建列表用来存放商品分类的数据
        goods_list =[]
        # 创建字典用来将分类名与该分类数据绑定
        typegoods = {}
        # 获得所有的可以展示商品
        goods = Goods.objects.filter(is_delete='0')
        # 获得所有的商品分类
        types = Goodclass.objects.all()
        # 循环所有的分类
        for type in types:
            # 创建初始值，记录每种分类数据只需要4条
            count = 0
            # 循环所有商品
            for good in goods:
                # 判断该商品是本次循环的类型
                if good.categoryid_id == type.id:
                    # 类型相同记录值加1
                    count += 1
                    # 将该数据加到列表中
                    goods_list.append(good)
                    # 到记录值到4时结束本次循环
                    if count == 4:
                        # 将类型名作为键，而保存在列表中的同类型的4条商品数据作为值，保存为键值对
                        typegoods[type.goodclassname] = goods_list
                        # 将列表制空以便下次循环
                        goods_list = []
                        # 跳出循环
                        break
        return render(request, 'app/index.html', {'i': i, 'imgs': img, 'typegoods': typegoods})


# 详情页
def detail(request):
    if request.method == 'GET':
        user = request.user
        if user.id:
            i = len(Cart.objects.filter(user=user))
        else:
            i = len(request.session.get('goods'))
        good_id = request.GET.get('good_id')
        good = Goods.objects.get(id=good_id)
        goods = Goods.objects.filter(categoryid=good.categoryid, recommend=1)
        #创建游览记录
        if user.id:
            visit = User_visit.objects.filter(user=user, goods=good).first()
            if not visit:
                User_visit.objects.create(user=user, goods=good)
            else:
                visit.visit_time = datetime.now()
                visit.save()


        return render(request, 'app/detail.html', {'good': good, 'goods': goods, 'i':i})


# 更多物品
def list(request):
    if request.method == 'GET':
        type_name = request.GET.get('type')
        page_num = int(request.GET.get('page', 1))
        goods = Goods.objects.filter(categoryid=Goodclass.objects.filter(goodclassname=type_name).first())
        goods = Paginator(goods, 10)
        page = goods.page(page_num)

        return render(request, 'app/list.html', {'page': page})


# 物品页面修改物品数量价格变动
@csrf_exempt
def good_money(request):
    if request.method == 'POST':
        good_id = request.POST.get('good_id')
        num = request.POST.get('num')
        good = Goods.objects.get(id= good_id)
        money = float(good.pirce) * float(num)
        money = '%.2f' % money
        data = {
            'code': 200,
            'msg': '请求成功',
            'money': money,
        }
        return JsonResponse(data)


# 添加物品到购物车
def addcart(request):
    if request.method == 'POST':
        user = request.user
        good_id = request.POST.get('good_id')
        num = request.POST.get('num')
        price = Goods.objects.filter(id=good_id).first().pirce
        imgname = Goods.objects.filter(id=good_id).first().goodsimg.name
        name = Goods.objects.filter(id=good_id).first().goodsname
        specifics = Goods.objects.filter(id=good_id).first().specifics
        goods_list = [good_id, num, '1', price, imgname, name, specifics]
        if user.id:
            good = Goods.objects.get(id=good_id)
            usercart = Cart.objects.filter(user=user,goods=good).first()
            if usercart:
                usercart.c_num += int(num)
                usercart.save()
            else:
                Cart.objects.create(user=user, goods=good, c_num=num)
            i = len(Cart.objects.filter(user=user))
            data = {
                'code': 200,
                'msg': '请求成功',
                'i': i
            }
            return JsonResponse(data)
        else:
            # 用户没有登录将添加的购物数据加到session中
            request.session['login_status'] = False
            # 判断session中是否存在goods字段（是否第一次存数据）
            if request.session.get('goods'):
                # 创建一个标识
                flag = 0
                # 循环session中的数据
                goods = request.session['goods']
                for session_goods in goods:
                    # 判断session中物品id是否与现在的相同
                    if session_goods[0] == good_id:
                        # id相同添加数量
                        session_goods[1] = int(session_goods[1]) + int(num)

                        # 将标识改为1
                        flag = 1
                        # 将数据写回session中
                        request.session['goods'] = goods
                        # session购物车的种类
                        i = len(request.session['goods'])
                # 判断标识为0时，创建新的sessiongoods数据
                if not flag:
                    # 获得session中的购物数据
                    goods = request.session['goods']
                    # 向购物数据中添加新的数据
                    goods.append(goods_list)
                    # 将数据写回session中
                    request.session['goods'] = goods
                    # session购物车的种类
                    i = len(request.session['goods'])
            else:
                # 首次添加商品的信息到session中，存入格式为列表
                goods = []
                goods.append(goods_list)
                request.session['goods'] = goods
                i = 1
            data = {
                'code': 200,
                'msg': '请求成功',
                'i': i
            }
            return JsonResponse(data)


#立即购买页面数据
def shop(request):
    if request.method == 'GET':
        user = request.user
        good_id = request.GET.get('good_id')
        num = request.GET.get('num')
        good= Goods.objects.filter(id=good_id).first()
        money = '%.2f' % (good.pirce * int(num))
        site = Adderss.objects.filter(user=user, is_select=1).first()
        if site:
            tel = miss_tel(site.tel)
            adderss = site
        data = {
            'adderss': site,
            'good': good,
            'money': money,
            'goodnum':num,
            'num': 1,
            'sum_money': float(money),
        }
        return render(request, 'app/order/place_order.html', data)


# 立即购买生成订单
def shop_order(request):
    if request.method == 'POST':
        user = request.user
        id = request.POST.get('id')
        num = request.POST.get('num')
        status = request.POST.get('status')
        o_num = get_order()
        good =Goods.objects.filter(id=id).first()
        money = '%.2f' %(good.pirce * int(num) +10)
        adderss = Adderss.objects.filter(user=user, is_select=1).first()
        order = Order.objects.create(user=user,
                                     o_num=o_num,
                                     o_money=money,
                                     o_status=status,
                                     adderss=adderss)
        OrderGoods.objects.create(order=order,
                                  goods=good,
                                  goods_num=num,
                                  goods_money=money)
        adderss.is_select = 0
        adderss.save()
        adderss = Adderss.objects.filter(user=user, is_default=1).first()
        adderss.is_select = 1
        adderss.save()
        if status == '1':
            return JsonResponse({'code': 200, 'msg': "请求成功", })
        else:
            return JsonResponse({'code': 2000, 'msg': "请求成功", })


# 建一个公共的计算钱的方法
def money(request):
    if request.method == 'GET':
        money = 0
        if request.user.id:
            user = request.user
            cartmoneys = Cart.objects.filter(user=user, is_select=1)
            for cartmoney in cartmoneys:
                money += int(cartmoney.c_num) * float(cartmoney.goods.pirce)
        else:
            goods = request.session.get('goods')
            i = len(goods)
            for index in range(i):
                if goods[index][2] == '1':
                    money += int(goods[index][1])*goods[index][3]
        money = '%.2f' % money
        data = {
            'code': 200,
            'msg': '请求成功',
            'money': money,
        }
        return JsonResponse(data)


# 查看购物车
def cart(request):
    if request.method == 'GET':
        user = request.user
        if user.id:
            cartgoods = Cart.objects.filter(user=user)
            for cart in cartgoods:
                cart.money = '%.2f' % (cart.c_num * cart.goods.pirce)
            i = 0
            for cartgood in cartgoods:
                i += 1
            return render(request, 'app/cart/cart.html', {'cartgoods': cartgoods, 'i': i})
        else:
            # 从session中拿商品的id
            goods = request.session.get('goods')
            for good in goods:
                good.append('%.2f' % (int(good[1])*good[3]))
            i = len(goods)
            return render(request, 'app/cart/cart.html', {'goods': goods, 'i': i})


# 修改购物车当中的数量
@csrf_exempt
def alter_cart_goods(request):
    if request.method == 'POST':
        user = request.user
        id = request.POST.get('cartgood_id')
        num = request.POST.get('num')
        if user.id:
            cart = Cart.objects.get(id=id)
            pirce = cart.goods.pirce
            cart.c_num = num
            cart.save()
            if num == '0':
                cart.delete()
        else:
            goods = request.session.get('goods')
            i = len(goods)
            if num == '0':
                for index in range(i):
                    if id == goods[index][0]:
                        goods.pop(index)
                        pirce = 0
                        break
            else:
                for index in range(i):
                    if id == goods[index][0]:
                        goods[index][1] = num
                        pirce = goods[index][3]
            # 将数据写回session中
            request.session['goods'] = goods
        data = {
            'code': 200,
            'msg': '请求成功',
            'pirce': pirce,
        }
        return JsonResponse(data)


# 修改购物车选中状态
def alter_cart_select(request):
    if request.method == 'POST':
        user = request.user
        id = request.POST.get('cartgood_id')
        if user.id:
            cart = Cart.objects.get(id=id)
            cart.is_select = 0 if cart.is_select else 1
            cart.save()
            select = cart.is_select
        else:
            goods = request.session.get('goods')
            i = len(goods)
            for good in goods:
                if good[0] == id:
                    good[2] = '0' if good[2] == '1' else '1'
                    select = good[2]
                    break
            # 将数据写回session中
            request.session['goods'] = goods
        data = {
            'code': 200,
            'msg': '请求成功',
            'select': select,

        }
        return JsonResponse(data)


# 判断是否全部勾选
def check_all(request):
    if request.method == 'GET':
        user = request.user
        if user.id:
            checkbox = Cart.objects.filter(is_select=0, user=user).exists()
            checkall = '0' if checkbox else '1'
        else:
            checkall = '1'
            goods = request.session.get('goods')
            i = len(goods)
            for index in range(i):
                if goods[index][2] == '0' :
                    checkall = '0'
                    break
        data = {
            'code': 200,
            'msg': '请求成功',
            'checkall': checkall,
        }
        return JsonResponse(data)


# 全选与反选
def goodsall(request):
    if request.method == 'GET':
        cartlist = []
        user = request.user
        if user.id:
            checkbox = Cart.objects.filter(is_select=0, user=user).exists()
            if checkbox:
                for cart in Cart.objects.filter(user=user):
                    cart.is_select = 1
                    cart.save()
                status = '1'
            else:
                for cart in Cart.objects.filter(user=user):
                    cart.is_select = 0
                    cart.save()
                status = '0'
            cartall = Cart.objects.filter(user=user)
            for cart in cartall:
                cartlist.append(cart.id)
        else:
            goods = request.session.get('goods')
            i = len(goods)
            flag = '1'
            status = '0'
            for index in range(i):
                if goods[index][2] == '0':
                    flag = '0'
                    status = '1'
                    break
            for index in range(i):
                if flag == '1':
                    goods[index][2] = '0'
                else:
                    goods[index][2] = '1'
            for good in goods:
                cartlist.append(good[0])
            # 将数据写回session中
            request.session['goods'] = goods
        data = {
            'code': 200,
            'msg': '请求成功',
            'status': status,
            'cartlist': cartlist,

        }
        return JsonResponse(data)


# 购物车界面购物车删除
def del_shop_car(request):
    if request.method == 'GET':
        id = request.GET.get('cartgood_id')
        if request.user.id:
            cart = Cart.objects.filter(id=id).first()
            cart.delete()
            data = {
                'code': 200,
                'msg': '请求成功',
            }
            return JsonResponse(data)
        else:
            goods = request.session.get('goods')
            i = len(goods)
            for index in range(i):
                if id == goods[index][0]:
                    goods.pop(index)
                    break
            # 将数据写回session中
            request.session['goods'] = goods
            data = {
                'code': 200,
                'msg': '请求成功',
            }
            return JsonResponse(data)


# 自动回调目前一共选中了选中了几件商品
def cartnum(request):
    if request.method == 'GET':
        selectncartnum = 0
        user = request.user
        if user.id:
            cart = Cart.objects.filter(user=user, is_select=1)
            for _ in cart:
                selectncartnum += 1
        else:
            goods = request.session.get('goods')
            i = len(goods)
            for index in range(i):
                if '1' == goods[index][2]:
                    selectncartnum += 1
        data = {
            'code': 200,
            'msg': '请求成功',
            'selectncartnum': selectncartnum,
        }
        return JsonResponse(data)


# 进入支付界面
def place_order(request):
    if request.method == 'GET':
        user = request.user
        order_id = request.GET.get('order_id', 1)
        if order_id == 1:
            # 判断是否有地址
            site = Adderss.objects.filter(user=user)
            if site:
                sites = '1'
            else:
                sites = '0'
            # 获得购物车信息
            carts = Cart.objects.filter(user=user, is_select=1)
            num = 0
            sum_money = 0
            for cart in carts:
                num += 1
                cart.money = round(float(cart.goods.pirce) * int(cart.c_num), 3)
                sum_money += cart.money
            sum_money = round(sum_money, 2)
            # 获得地址
            site = Adderss.objects.filter(user=user, is_select=1).first()
            if site:
                tel = miss_tel(site.tel)
                adderss = site
            else:
                tel = 0
                adderss = 0
            pay = '0'
            data = {
                'carts': carts,
                'site': sites,
                'tel': tel,
                'num': num,
                'sum_money': sum_money,
                'adderss': adderss,
                'pay': pay,
                'order_id': order_id
            }
            return render(request, 'app/order/place_order.html', data)
        else:
            oredr = Order.objects.filter(o_num=order_id).first()
            carts = OrderGoods.objects.filter(order=oredr)
            num = 0
            for cart in carts:
                num += 1
            sum_money = float(oredr.o_money)
            adderss = Adderss.objects.filter(id=int(oredr.adderss_id)).first()
            tel = miss_tel(adderss.tel)
            sites = '1'
            pay = '1'

            data = {
                'carts': carts,
                'site': sites,
                'tel': tel,
                'num': num,
                'sum_money': sum_money,
                'adderss': adderss,
                'pay': pay,
                'order_id': order_id
            }
            addersses = Adderss.objects.filter(user=user, is_default=1).first()
            addersses.is_select = 0
            addersses.save()
            adderss.is_select = 1
            adderss.save()
            return render(request, 'app/order/place_order.html', data)


# 选择临时地址界面
def select_adderss(request):
    if request.method == 'GET':
        user = request.user
        order_id =request.GET.get('order_id')
        site = Adderss.objects.filter(user=user)
        data = {
            'code': 200,
            'msg': '请求成功',
            'sites': site,
            'order_id': order_id
        }
        return render(request, 'app/order/select_adderss.html', data)


# 选择临时使用地址
def use_site(request):
    if request.method == 'GET':
        id = request.GET.get('site_id')
        order_id = request.GET.get('order_id')
        site = Adderss.objects.filter(id=id).first()
        order = Order.objects.filter(o_num=order_id).first()
        adderss = Adderss.objects.filter(is_select=1).first()
        if order:
            adderss.is_select = 0
            adderss.save()
            site.is_select = 1
            site.save()
            order.adderss = site
            order.save()
        else:
            adderss.is_select = 0
            adderss.save()
            site.is_select = 1
            site.save()
        data = {
            'code': 200,
            'msg': '请求成功'
        }
        return JsonResponse(data)


# 支付
def order_pay(request):
    if request.method == 'POST':
        user = request.user
        # 产生订单编号
        o_num = get_order()
        # 获取用户购物车信息
        carts = Cart.objects.filter(user=user, is_select=1)
        # 计算购物车总金额
        o_money = 0
        for cart in carts:
            o_money += round(cart.c_num * cart.goods.pirce, 2)
        o_money = round(o_money, 2)
        # 创建订单
        o_status = request.POST.get('num')
        # 找到用户使用地址
        adderss = Adderss.objects.filter(user=user, is_select=1).first()
        order = Order.objects.create(user=user,
                                     o_num=o_num,
                                     o_money=o_money,
                                     o_status=o_status,
                                     adderss=adderss)
        # 创建订单商品详情表
        for c in carts:
            OrderGoods.objects.create(order=order,
                                      goods=c.goods,
                                      goods_num=c.c_num,
                                      goods_money=round(c.c_num * c.goods.pirce, 2))
        carts.delete()
        adderss.is_select = 0
        adderss.save()
        adderss =Adderss.objects.filter(user=user, is_default=1 ).first()
        adderss.is_select = 1
        adderss.save()
        return JsonResponse({'code': 200, 'msg': "请求成功", 'order_id': o_num})


# 支付(未支付订单)
def order_status(request):
    if request.method == 'POST':
        user = request.user
        order_id = request.POST.get('order_id')
        status = request.POST.get('num')
        order = Order.objects.filter(o_num=order_id).first()

        # 找到用户使用地址
        adderss = Adderss.objects.filter(user=user, is_select=1).first()
        order.adderss =adderss
        order.save()
        adderss.is_select = 0
        adderss.save()
        adderss = Adderss.objects.filter(user=user, is_default=1).first()
        adderss.is_select = 1
        adderss.save()
        if status == '1':
            order.o_status = 1
            order.save()
            return JsonResponse({'code': 200, 'msg': "请求成功", })
        else:
            return JsonResponse({'code': 2000, 'msg': "请求成功", })


# 订单页
def user_center_order(request):
    if request.method == 'GET':
        user = request.user
        orders = Order.objects.filter(user=user)
        # for order in orders:
        #     order.o = str(order.o_create.strftime('%Y-%m-%d %H:%M:%S'))
        page_num = int(request.GET.get('page', 1))
        goods = Paginator(orders, 2)
        page = goods.page(page_num)
        return render(request, 'app/user/user_center_order.html', {'page': page})


# 地址编辑页面
def user_center_site(request):
    if request.method == 'GET':
        user = request.user
        site = Adderss.objects.filter(user=user)
        data = {
            'code': 200,
            'msg': '请求成功',
            'sites': site,
        }
        return render(request, 'app/user/user_center_site.html', data)


# 添加地址
def add_adderss(request):
    if request.method == 'GET':
        return render(request, 'app/user/user_add_adderss.html')
    if request.method == 'POST':
        user = request.user
        recipients = request.POST.get('recipients')
        addersss = request.POST.get('addersss')
        postcode = request.POST.get('postcode')
        tel = request.POST.get('tel')
        site = Adderss.objects.filter(user=user)
        if not site:
            Adderss.objects.create(recipients=recipients,
                                   addersss=addersss,
                                   postcode=postcode,
                                   tel=tel,
                                   user=user,
                                   is_default=1,
                                   is_select=1)
        else:
            Adderss.objects.create(recipients=recipients,
                                   addersss=addersss,
                                   postcode=postcode,
                                   tel=tel,
                                   user=user,
                                   )
        data = {'code': 200, 'msg': '请求成功.', }
        return JsonResponse(data)


# 删除地址
def deltet_adderss(request):
    if request.method == 'POST':
        site_id = request.POST.get('site_id')
        site = Adderss.objects.get(id=site_id)
        site.delete()
        data = {
            'code': 200,
            'msg': '请求成功'
        }
        return JsonResponse(data)


# 获得单条地址信息进行编辑
def site(request):
    if request.method == 'GET':
        site_id = request.GET.get('site_id')
        site = Adderss.objects.get(id=site_id)
        data = {
            'code': 200,
            'recipients': site.recipients,
            'addersss': site.addersss,
            'postcode': site.postcode ,
            'tel': site.tel,
        }
        return JsonResponse(data)


# 修改地址信息方法
def mod_site(request):
    if request.method == 'POST':
        recipients = request.POST.get('recipients')
        addersss = request.POST.get('addersss')
        postcode = request.POST.get('postcode')
        tel = request.POST.get('tel')
        site_id = request.POST.get('site_id')
        site = Adderss.objects.get(id=site_id)
        site.recipients = recipients
        site.addersss = addersss
        site.postcode = postcode
        site.tel = tel
        site.save()
        site = Adderss.objects.get(id=site_id)
        data = {
            'code': 200,
            'msg': '请求成功',
            'code': 200,
            'recipients': site.recipients,
            'addersss': site.addersss,
            'postcode': site.postcode,
            'tel': site.tel,

        }
        return JsonResponse(data)


# 修改默认地址
def use(request):
    if request.method == 'GET':
        user = request.user
        site_id = request.GET.get('site_id')
        replace_site = Adderss.objects.get(id=site_id)
        default_site = Adderss.objects.filter(user=user, is_default=1).first()
        default_site.is_default = '0'
        default_site.is_select = '0'
        default_site.save()
        replace_site.is_default = '1'
        replace_site.is_select = '1'
        replace_site.save()
        data = {
            'code': 200,
            'msg': '请求成功',
        }
        return JsonResponse(data)


# 用户信息页面
def user_center_info(request):
    if request.method == 'GET':
        user = request.user
        visit = User_visit.objects.order_by('-visit_time')[0:5]
        return render(request, 'app/user/user_center_info.html', {'user': user, 'visit': visit})
    if request.method == 'POST':
        user = request.user
        adderss = request.POST.get('adderss')
        tel = request.POST.get('tel')
        user.addersss=adderss
        user.tel=tel
        user.save()
        visit = User_visit.objects.order_by('-visit_time')[0:5]
        return render(request, 'app/user/user_center_info.html', {'user': user, 'visit': visit})

# 搜索
def seek(request):
    if request.method == 'GET':
        seek = request.GET.get('seek')

        goods = Goods.objects.filter(goodsname__icontains=seek)
        page_num = int(request.GET.get('page', 1))
        goods = Paginator(goods, 10)
        page = goods.page(page_num)
        user = request.user
        if user:
            if user.id:
                i = len(Cart.objects.filter(user=user))
        else:
            i = len(request.session.get('goods'))
        return render(request, 'app/seek/seek.html', {'page': page, 'i': i, 'seek': seek})

