
import streamlit as st
from supabase import create_client


def allowed_emails():
    try:
        return {str(x).strip().lower() for x in st.secrets.get("ALLOWED_EMAILS", [])}
    except Exception:
        return set()


def make_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def init_auth():
    if "sb" not in st.session_state:
        st.session_state.sb = make_client()
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_session" not in st.session_state:
        st.session_state.auth_session = None


def sign_in(email: str, password: str):
    sb = st.session_state.sb
    response = sb.auth.sign_in_with_password(
        {"email": email.strip().lower(), "password": password}
    )
    st.session_state.auth_user = response.user
    st.session_state.auth_session = response.session
    return response


def sign_up(email: str, password: str):
    email = email.strip().lower()
    allowed = allowed_emails()
    if allowed and email not in allowed:
        raise ValueError("Este e-mail não está autorizado a criar conta nesta plataforma.")

    sb = st.session_state.sb
    response = sb.auth.sign_up(
        {"email": email, "password": password}
    )
    return response


def sign_out():
    try:
        st.session_state.sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.auth_user = None
    st.session_state.auth_session = None


def current_user_id():
    user = st.session_state.get("auth_user")
    return str(user.id) if user else None


def require_login():
    init_auth()

    if st.session_state.auth_user is not None:
        return True

    st.markdown(
        """
        <div class="login-wrap">
          <div class="login-brand">P</div>
          <h1>Painel Patrimonial</h1>
          <p>Acompanhe sua carteira em um ambiente pessoal e protegido.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            if submit:
                try:
                    sign_in(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível entrar: {e}")

    with tab_signup:
        st.caption("Somente e-mails autorizados em ALLOWED_EMAILS podem criar conta.")
        with st.form("signup_form"):
            email = st.text_input("E-mail autorizado", key="signup_email")
            password = st.text_input("Crie uma senha", type="password", key="signup_password")
            confirm = st.text_input("Repita a senha", type="password", key="signup_confirm")
            submit = st.form_submit_button("Criar conta", use_container_width=True)

            if submit:
                if len(password) < 8:
                    st.error("A senha deve ter pelo menos 8 caracteres.")
                elif password != confirm:
                    st.error("As senhas não coincidem.")
                else:
                    try:
                        response = sign_up(email, password)
                        if response.session:
                            st.session_state.auth_user = response.user
                            st.session_state.auth_session = response.session
                            st.rerun()
                        else:
                            st.success("Conta criada. Verifique seu e-mail para confirmar o acesso.")
                    except Exception as e:
                        st.error(f"Não foi possível criar a conta: {e}")

    return False
