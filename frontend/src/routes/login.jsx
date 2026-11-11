import { LoginPage } from "../pages/LoginPage";

export function LoginRoute({ auth, onAuthenticated }) {
  return <LoginPage auth={auth} onAuthenticated={onAuthenticated} />;
}
