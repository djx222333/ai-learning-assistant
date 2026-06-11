// 共享 Axios 实例
// 自动注入 JWT Token + 401 全局处理

import axios from "axios";

const http = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

// 请求拦截器：自动注入 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem("ai_learning_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 时清除 token
http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("ai_learning_token");
      localStorage.removeItem("ai_learning_user");
      // 触发全局事件，AuthContext 会监听
      window.dispatchEvent(new CustomEvent("auth:logout"));
    }
    return Promise.reject(error);
  }
);

export default http;