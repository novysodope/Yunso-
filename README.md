# yunso
```bash
____    ____  __    __  .__   __.      _______.  ______
\   \  /   / |  |  |  | |  \ |  |     /       | /  __  \
 \   \/   /  |  |  |  | |   \|  |    |   (----`|  |  |  |
  \_    _/   |  |  |  | |  . `  |     \   \    |  |  |  |
    |  |     |  `--'  | |  |\   | .----)   |   |  `--'  |
    |__|      \______/  |__| \__| |_______/     \______/

https://github.com/novysodope/yunso      云索|Fupo Series
```

利用wxauto库写的微信推送脚本，利用Github API的语法监控Github最新动态和搜索Github内容，效果看最后

代码易懂，注释已给出

# 使用前提
- python3.8
- windows（必须）
- 微信(测试最新版3.9.12.37可用）
- 填写好配置后，运行脚本之前**一定要登录好微信，且电脑不可锁屏**，推荐使用云服务器，然后使用VNC登录，这样断开连接的时候就不会自动锁屏了（mstsc断开连接会自动锁屏）
# 配置
运行之前请先填写配置文件 yunso_config.ini
```bash
[DEFAULT]
GITHUB_API_KEY = 必填，填写Github访问令牌，创建链接：https://github.com/settings/tokens，教程：https://blog.csdn.net/m0_46918768/article/details/144763839
listen_list = 必填，填写发送对象，如果有多个对象以,分隔
me = 必填，填写机器人所在群聊的备注名称
black_keywords = 可选，填写黑名单关键字
search_keywords = 默认提供有，可以自己新加，以,分隔

示例:
[DEFAULT]
GITHUB_API_KEY = AAAXXXXAXAXAXAXAXiamnovyhhh
listen_list = 群聊A,群聊B,用户A
me = 二狗
black_keywords = 啥比
search_keywords = CVE-20,CNVD-20,CNVD-C-20,CNNVD-20,命令执行漏洞,SQL注入,代码执行漏洞,命令注入漏洞,反序列化漏洞,资源管理错误,信息泄露,未授权访问,任意文件读取漏洞,目录遍历,任意文件下载漏洞,任意文件上传漏洞,未经身份验证的攻击者,Vulnerability-CVE,RCE-Vulnerability,RCE-POC
```
# 运行
- pip install -r requirements.txt 下载好需要的库
- python3 yunso.py

# 效果
![image](https://github.com/user-attachments/assets/92c201e2-e429-4302-87d4-94508e65087c)

![image](https://github.com/user-attachments/assets/c8398c09-043b-4bfb-9f04-eef4525d05f0)

![image](https://github.com/user-attachments/assets/c7492c28-ceb5-4ff3-a7d3-5a41fd8692ec)



# 其他
- 考虑到在云服务器运行的话，人看不到脚本状态，所以加上了“心跳”
```python
print("没有新内容，开始表明存活状态")
self.wx.GetSessionList()
self.wx.SendMsg("online", '文件传输助手')
```
这样就能知道脚本是否还在运行：

![1739254131303](https://github.com/user-attachments/assets/4fc8f7a4-9d0c-46b2-b5e6-d38dd216f2cb)



# 可能遇到的问题
- 偶发事件，打开微信后，可能无法打开对话窗口，这个时候需要手动把聊天窗口单独拖出来就可以了，**注意：**打开后就不能关掉了，放服务器挂着就行了
- 偶发事件，艾特他搜索的时候，回复有延迟是正常的，大概2秒左右。如果回复“搜索异常”也没关系，他还会继续回复搜索结果，这是个bug，抽空解决



因为github的搜索结果有的太露骨，搜索功能已删除，避免被有心之人利用
