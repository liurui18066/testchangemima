# app.py
import reflex as rx
import httpx
import socket
def get_local_ip():
    """获取本机局域网IP"""
    try:
        # 创建一个临时连接来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class AuthState(rx.State):
    """认证状态管理"""
    
    # 状态变量
    show_forgot_password: bool = False  # 是否显示忘记密码界面
    forgot_email: str = ""  # 用户输入的邮箱
    forgot_message: str = ""  # 显示给用户的消息
    message_type: str = "info"  # 消息类型: info, success, error
    email_sent: bool = False  # 邮件是否已发送
    server_ip: str = "127.0.0.1"  # 服务器IP地址

    def toggle_forgot_password(self):
        """切换忘记密码界面显示状态"""
        self.show_forgot_password = not self.show_forgot_password
        self.forgot_message = ""
        self.email_sent = False
    
    def on_load(self):
        """页面加载时获取服务器IP"""
        ip = get_local_ip()
        self.server_ip = ip if ip != "127.0.0.1" else self.server_ip

    async def handle_forgot_password(self):
        """调用Go后端发送重置链接"""
        
        # 邮箱验证
        if not self.forgot_email:
            self.forgot_message = "请输入邮箱地址"
            self.message_type = "error"
            return
        
        if "@" not in self.forgot_email or "." not in self.forgot_email:
            self.forgot_message = "请输入有效的邮箱地址"
            self.message_type = "error"
            return
        
        # 显示加载状态
        self.forgot_message = "正在发送重置链接，请稍候..."
        self.message_type = "info"
        
        try:
            async with httpx.AsyncClient() as client:
                reset_url = f"http://{self.server_ip}:3000/reset-password"
                # 调用Go后端API
                response = await client.post(
                    "http://localhost:8080/api/forgot-password",
                    json={
                        "email": self.forgot_email,
                        "reset_url": reset_url  # 使用实际IP地址  # 重置页面URL
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        self.forgot_message = f"重置链接已发送到 {self.forgot_email}，请检查您的邮箱"
                        self.message_type = "success"
                        self.email_sent = True
                        
                        # 记录发送的token（实际应用中可能需要保存到数据库）
                        reset_token = result.get("reset_token", "12345")
                        if reset_token:
                            print(f"重置Token: {reset_token}")
                            # 这里可以保存token到状态或数据库，用于后续验证
                    else:
                        error_msg = result.get("message", "发送失败，请稍后重试")
                        self.forgot_message = f"发送失败: {error_msg}"
                        self.message_type = "error"
                elif response.status_code == 404:
                    self.forgot_message = "该邮箱未注册"
                    self.message_type = "error"
                else:
                    self.forgot_message = f"服务器错误 (状态码: {response.status_code})"
                    self.message_type = "error"
                    
        except httpx.TimeoutException:
            self.forgot_message = "请求超时，请检查网络连接"
            self.message_type = "error"
        except httpx.RequestError:
            self.forgot_message = "无法连接到服务器，请稍后重试"
            self.message_type = "error"
        except Exception as e:
            self.forgot_message = f"发生未知错误: {str(e)}"
            self.message_type = "error"
    
    def reset_form(self):
        """重置表单状态"""
        self.forgot_email = ""
        self.forgot_message = ""
        self.email_sent = False
        self.show_forgot_password = False


def login_form() -> rx.Component:
    """登录表单组件"""
    return rx.box(
        rx.vstack(
            rx.heading("用户登录", size="4"),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="请输入邮箱",
                        type="email",
                        size="3",
                        width="100%",
                        mb=2,
                    ),
                    rx.input(
                        placeholder="请输入密码",
                        type="password",
                        size="3",
                        width="100%",
                        mb=4,
                    ),
                    rx.button(
                        "登录",
                        type="submit",
                        size="3",
                        width="100%",
                        color_scheme="blue",
                    ),
                    align="center",
                ),
                width="100%",
            ),
            rx.divider(margin="1em 0"),
            rx.link(
                rx.button(
                    "忘记密码?",
                    variant="ghost",
                    size="3",
                    on_click=AuthState.toggle_forgot_password,
                ),
                underline="hover",
            ),
            rx.text(
                "还没有账号? ",
                rx.link("立即注册", href="/register", underline="hover"),
                color="gray",
                size="3",
            ),
            width="100%",
            max_width="400px",
            padding="2em",
            bg="white",
            border_radius="lg",
            box_shadow="lg",
        ),
        display="flex",
        justify_content="center",
        align_items="center",
        height="100vh",
        bg="gray.50",
    )


def forgot_password_form() -> rx.Component:
    """忘记密码表单组件"""
    return rx.box(
        rx.vstack(
            rx.heading("重置密码", size="4"),
            rx.text(
                "请输入您的注册邮箱，我们将发送重置链接",
                color="gray",
                text_align="center",
                mb=4,
            ),
            
            # 消息显示
            rx.cond(
                AuthState.forgot_message != "",
                rx.box(
                    rx.text(
                        AuthState.forgot_message,
                        color=rx.cond(
                            AuthState.message_type == "success",
                            "green.600",
                            rx.cond(
                                AuthState.message_type == "error",
                                "red.600",
                                "blue.600"
                            )
                        ),
                        bg=rx.cond(
                            AuthState.message_type == "success",
                            "green.50",
                            rx.cond(
                                AuthState.message_type == "error",
                                "red.50",
                                "blue.50"
                            )
                        ),
                        padding="0.75em",
                        border_radius="md",
                        width="100%",
                    ),
                    width="100%",
                    mb=4,
                )
            ),
            
            # 成功发送后的提示
            rx.cond(
                AuthState.email_sent,
                rx.vstack(
                    rx.icon(
                        tag="check_circle",
                        color="green.500",
                        size=24,
                    ),
                    rx.text(
                        "重置链接已发送！",
                        size="4",
                        font_weight="bold",
                    ),
                    rx.text(
                        "请检查您的邮箱并点击重置链接。链接在30分钟内有效。",
                        color="gray",
                        text_align="center",
                        size="3",
                    ),
                    rx.button(
                        "返回登录",
                        on_click=AuthState.toggle_forgot_password,
                        mt=4,
                        variant="outline",
                        size="3",
                    ),
                    align="center",
                    spacing="3",  # 修复：字符串"3"，而不是整数3
                    width="100%",
                ),
                # 邮箱输入表单
                rx.form(
                    rx.vstack(
                        rx.input(
                            placeholder="请输入注册邮箱",
                            type="email",
                            value=AuthState.forgot_email,
                            on_change=AuthState.set_forgot_email,
                            size="3",
                            width="100%",
                            mb=4,
                        ),
                        rx.button(
                            "发送重置链接",
                            type="submit",
                            size="3",
                            width="100%",
                            color_scheme="blue",
                            #on_click=AuthState.handle_forgot_password,
                        ),
                        rx.button(
                            "返回登录",
                            on_click=AuthState.toggle_forgot_password,
                            variant="ghost",
                            width="100%",
                            size="3",
                        ),
                        align="center",
                    ),
                    width="100%",
                    on_submit=AuthState.handle_forgot_password,
                )
            ),
            
            width="100%",
            max_width="400px",
            padding="2em",
            bg="white",
            border_radius="lg",
            box_shadow="lg",
        ),
        display="flex",
        justify_content="center",
        align_items="center",
        height="100vh",
        bg="gray.50",
    )


def reset_password_page() -> rx.Component:
    """重置密码页面（用户通过邮箱链接访问）"""
    return rx.box(
        rx.vstack(
            rx.heading("设置新密码", size="4"),
            rx.text(
                "请输入您的新密码",
                color="gray",
                mb=4,
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="新密码",
                        type="password",
                        size="3",
                        width="100%",
                        mb=2,
                    ),
                    rx.input(
                        placeholder="确认新密码",
                        type="password",
                        size="3",
                        width="100%",
                        mb=4,
                    ),
                    rx.button(
                        "重置密码",
                        type="submit",
                        size="3",
                        width="100%",
                        color_scheme="blue",
                    ),
                    align="center",
                ),
                width="100%",
            ),
            width="100%",
            max_width="400px",
            padding="2em",
            bg="white",
            border_radius="lg",
            box_shadow="lg",
        ),
        display="flex",
        justify_content="center",
        align_items="center",
        height="100vh",
        bg="gray.50",
    )


def index() -> rx.Component:
    """主页面，根据状态显示登录或忘记密码界面"""
    return rx.cond(
        AuthState.show_forgot_password,
        forgot_password_form(),
        login_form()
    )


# 创建应用
app = rx.App()
app.add_page(index, route="/", title="用户登录")
app.add_page(reset_password_page, route="/reset-password", title="重置密码")