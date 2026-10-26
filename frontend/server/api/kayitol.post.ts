import { authProxy } from '../utils/authProxy'
export default defineEventHandler((event) => authProxy(event, 'register', 'POST'))
