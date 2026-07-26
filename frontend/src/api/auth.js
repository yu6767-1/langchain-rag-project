/**
 * 认证 API
 */

import request from './request'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function register(username, password) {
  return request.post('/auth/register', { username, password })
}

export function changePassword(oldPassword, newPassword) {
  return request.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export function getCurrentUser() {
  return request.get('/auth/me')
}
