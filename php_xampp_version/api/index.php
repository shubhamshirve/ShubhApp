<?php
/**
 * Multi-Tenant SaaS Recurring Billing Platform
 * API Router for PHP/XAMPP
 */

require_once 'config.php';

// Enable CORS
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Get request info
$method = $_SERVER['REQUEST_METHOD'];
$uri = $_SERVER['REQUEST_URI'];
$path = parse_url($uri, PHP_URL_PATH);
$path = str_replace('/saas-billing/api', '', $path);
$path = rtrim($path, '/');

// Get JSON input
$input = json_decode(file_get_contents('php://input'), true) ?? [];

// Get database connection
$db = Database::getInstance()->getConnection();

// Route handling
switch (true) {
    // Health Check
    case $method === 'GET' && $path === '/health':
        jsonResponse(['status' => 'healthy', 'service' => 'Multi-Tenant SaaS Billing Platform']);
        break;

    // ==================== AUTH ROUTES ====================
    
    // Register Operator
    case $method === 'POST' && $path === '/auth/register':
        $required = ['company_name', 'owner_name', 'email', 'phone', 'password'];
        foreach ($required as $field) {
            if (empty($input[$field])) {
                jsonResponse(['error' => "Field '$field' is required"], 400);
            }
        }
        
        // Check if email exists
        $stmt = $db->prepare("SELECT id FROM users WHERE email = ? AND deleted_at IS NULL");
        $stmt->execute([$input['email']]);
        if ($stmt->fetch()) {
            jsonResponse(['error' => 'Email already registered'], 400);
        }
        
        // Get trial plan
        $stmt = $db->prepare("SELECT * FROM saas_plans WHERE trial_enabled = 1 AND deleted_at IS NULL LIMIT 1");
        $stmt->execute();
        $trialPlan = $stmt->fetch();
        
        $operatorId = generateUUID();
        $userId = generateUUID();
        $trialEnds = date('Y-m-d H:i:s', strtotime('+' . ($trialPlan['trial_days'] ?? 3) . ' days'));
        
        // Create operator
        $stmt = $db->prepare("INSERT INTO operators (id, company_name, owner_name, email, phone, gst_number, charge_gst, status, saas_plan_id, saas_plan_name, trial_ends_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'trial', ?, ?, ?)");
        $stmt->execute([
            $operatorId,
            $input['company_name'],
            $input['owner_name'],
            $input['email'],
            $input['phone'],
            $input['gst_number'] ?? null,
            $input['charge_gst'] ?? false,
            $trialPlan['id'] ?? null,
            $trialPlan['name'] ?? null,
            $trialEnds
        ]);
        
        // Create user
        $stmt = $db->prepare("INSERT INTO users (id, email, name, phone, password, role, operator_id, status) VALUES (?, ?, ?, ?, ?, 'operator', ?, 'active')");
        $stmt->execute([
            $userId,
            $input['email'],
            $input['owner_name'],
            $input['phone'],
            hashPassword($input['password']),
            $operatorId
        ]);
        
        $token = createJWT([
            'sub' => $userId,
            'email' => $input['email'],
            'role' => 'operator',
            'operator_id' => $operatorId
        ]);
        
        jsonResponse([
            'access_token' => $token,
            'token_type' => 'bearer',
            'user' => [
                'id' => $userId,
                'email' => $input['email'],
                'name' => $input['owner_name'],
                'role' => 'operator',
                'operator_id' => $operatorId,
                'status' => 'active'
            ]
        ]);
        break;

    // Login
    case $method === 'POST' && $path === '/auth/login':
        if (empty($input['email']) || empty($input['password'])) {
            jsonResponse(['error' => 'Email and password required'], 400);
        }
        
        $stmt = $db->prepare("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL");
        $stmt->execute([$input['email']]);
        $user = $stmt->fetch();
        
        if (!$user || !verifyPassword($input['password'], $user['password'])) {
            jsonResponse(['error' => 'Invalid credentials'], 401);
        }
        
        if ($user['status'] !== 'active') {
            jsonResponse(['error' => 'Account is not active'], 401);
        }
        
        $token = createJWT([
            'sub' => $user['id'],
            'email' => $user['email'],
            'role' => $user['role'],
            'operator_id' => $user['operator_id']
        ]);
        
        jsonResponse([
            'access_token' => $token,
            'token_type' => 'bearer',
            'user' => [
                'id' => $user['id'],
                'email' => $user['email'],
                'name' => $user['name'],
                'phone' => $user['phone'],
                'role' => $user['role'],
                'operator_id' => $user['operator_id'],
                'status' => $user['status']
            ]
        ]);
        break;

    // Get Current User
    case $method === 'GET' && $path === '/auth/me':
        $user = requireAuth();
        $stmt = $db->prepare("SELECT id, email, name, phone, role, operator_id, status, created_at FROM users WHERE id = ?");
        $stmt->execute([$user['sub']]);
        jsonResponse($stmt->fetch());
        break;

    // ==================== ADMIN ROUTES ====================
    
    // Admin Dashboard
    case $method === 'GET' && $path === '/admin/dashboard':
        requireAdmin();
        
        $stats = [];
        
        $stmt = $db->query("SELECT COUNT(*) as count FROM operators WHERE deleted_at IS NULL");
        $stats['total_operators'] = $stmt->fetch()['count'];
        
        $stmt = $db->query("SELECT COUNT(*) as count FROM operators WHERE status = 'active' AND deleted_at IS NULL");
        $stats['active_operators'] = $stmt->fetch()['count'];
        
        $stmt = $db->query("SELECT COUNT(*) as count FROM operators WHERE status = 'trial' AND deleted_at IS NULL");
        $stats['trial_operators'] = $stmt->fetch()['count'];
        
        $stmt = $db->query("SELECT COUNT(*) as count FROM operators WHERE status = 'suspended' AND deleted_at IS NULL");
        $stats['suspended_operators'] = $stmt->fetch()['count'];
        
        $stmt = $db->query("SELECT COUNT(*) as count FROM operators WHERE is_read_only = 1 AND deleted_at IS NULL");
        $stats['read_only_operators'] = $stmt->fetch()['count'];
        
        $expiringDate = date('Y-m-d H:i:s', strtotime('+7 days'));
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM operators WHERE subscription_ends_at <= ? AND subscription_ends_at >= NOW() AND deleted_at IS NULL");
        $stmt->execute([$expiringDate]);
        $stats['expiring_operators'] = $stmt->fetch()['count'];
        
        $stats['saas_revenue_this_month'] = 0;
        $stats['gst_collected'] = 0;
        $stats['addon_revenue'] = 0;
        
        jsonResponse($stats);
        break;

    // Admin SaaS Plans CRUD
    case $method === 'GET' && $path === '/admin/saas-plans':
        requireAdmin();
        $stmt = $db->query("SELECT * FROM saas_plans WHERE deleted_at IS NULL ORDER BY monthly_price ASC");
        jsonResponse($stmt->fetchAll());
        break;
    
    case $method === 'POST' && $path === '/admin/saas-plans':
        requireAdmin();
        $id = generateUUID();
        $stmt = $db->prepare("INSERT INTO saas_plans (id, name, monthly_price, max_subscribers, max_staff, trial_enabled, trial_days, notification_module, auto_reminder, audit_logs, payment_gateway_setup, gst_applicable) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->execute([
            $id,
            $input['name'],
            $input['monthly_price'],
            $input['max_subscribers'],
            $input['max_staff'],
            $input['trial_enabled'] ?? false,
            $input['trial_days'] ?? 0,
            $input['notification_module'] ?? false,
            $input['auto_reminder'] ?? false,
            $input['audit_logs'] ?? false,
            $input['payment_gateway_setup'] ?? false,
            $input['gst_applicable'] ?? true
        ]);
        $stmt = $db->prepare("SELECT * FROM saas_plans WHERE id = ?");
        $stmt->execute([$id]);
        jsonResponse($stmt->fetch(), 201);
        break;

    // Admin Operators
    case $method === 'GET' && $path === '/admin/operators':
        requireAdmin();
        $stmt = $db->query("SELECT * FROM operators WHERE deleted_at IS NULL ORDER BY created_at DESC");
        jsonResponse($stmt->fetchAll());
        break;

    // Admin Assign Plan to Operator
    case $method === 'POST' && preg_match('/^\/admin\/operators\/([^\/]+)\/assign-plan$/', $path, $matches):
        requireAdmin();
        $operatorId = $matches[1];
        $planId = $_GET['plan_id'] ?? $input['plan_id'] ?? null;
        
        if (!$planId) {
            jsonResponse(['error' => 'Plan ID required'], 400);
        }
        
        $stmt = $db->prepare("SELECT * FROM saas_plans WHERE id = ? AND deleted_at IS NULL");
        $stmt->execute([$planId]);
        $plan = $stmt->fetch();
        
        if (!$plan) {
            jsonResponse(['error' => 'Plan not found'], 404);
        }
        
        $subscriptionEnds = date('Y-m-d H:i:s', strtotime('+30 days'));
        $stmt = $db->prepare("UPDATE operators SET saas_plan_id = ?, saas_plan_name = ?, status = 'active', subscription_ends_at = ?, is_read_only = 0 WHERE id = ?");
        $stmt->execute([$planId, $plan['name'], $subscriptionEnds, $operatorId]);
        
        jsonResponse(['message' => 'Plan assigned successfully']);
        break;

    // Admin Audit Logs
    case $method === 'GET' && $path === '/admin/audit-logs':
        requireAdmin();
        $limit = $_GET['limit'] ?? 50;
        $stmt = $db->prepare("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?");
        $stmt->execute([(int)$limit]);
        jsonResponse($stmt->fetchAll());
        break;

    // ==================== OPERATOR ROUTES ====================
    
    // Operator Dashboard
    case $method === 'GET' && $path === '/operator/dashboard':
        $user = requireOperator();
        if ($user['role'] === 'admin') {
            jsonResponse(['error' => 'Use admin dashboard'], 400);
        }
        
        $operatorId = $user['operator_id'];
        $stats = [];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM subscribers WHERE operator_id = ? AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['total_subscribers'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM subscribers WHERE operator_id = ? AND status = 'active' AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['active_subscribers'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM invoices WHERE operator_id = ? AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['total_invoices'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM invoices WHERE operator_id = ? AND status = 'pending' AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['pending_invoices'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM invoices WHERE operator_id = ? AND status = 'overdue' AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['overdue_invoices'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COUNT(*) as count FROM invoices WHERE operator_id = ? AND status = 'paid' AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['paid_invoices'] = $stmt->fetch()['count'];
        
        $stmt = $db->prepare("SELECT COALESCE(SUM(final_amount), 0) as total FROM invoices WHERE operator_id = ? AND status = 'paid' AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $stats['total_revenue'] = $stmt->fetch()['total'];
        
        $stmt = $db->prepare("SELECT * FROM operators WHERE id = ? AND deleted_at IS NULL");
        $stmt->execute([$operatorId]);
        $operator = $stmt->fetch();
        
        $stats['is_read_only'] = (bool)$operator['is_read_only'];
        $stats['subscription_ends_at'] = $operator['subscription_ends_at'];
        $stats['trial_ends_at'] = $operator['trial_ends_at'];
        $stats['status'] = $operator['status'];
        
        jsonResponse($stats);
        break;

    // Operator Profile
    case $method === 'GET' && $path === '/operator/profile':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT * FROM operators WHERE id = ? AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        jsonResponse($stmt->fetch());
        break;

    // Operator Plans CRUD
    case $method === 'GET' && $path === '/operator/plans':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT * FROM operator_plans WHERE operator_id = ? AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        jsonResponse($stmt->fetchAll());
        break;
    
    case $method === 'POST' && $path === '/operator/plans':
        $user = requireOperator();
        $id = generateUUID();
        $stmt = $db->prepare("INSERT INTO operator_plans (id, operator_id, name, price, validity, tax_percentage, tax_type, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->execute([
            $id,
            $user['operator_id'],
            $input['name'],
            $input['price'],
            $input['validity'] ?? 'monthly',
            $input['tax_percentage'] ?? 0,
            $input['tax_type'] ?? 'none',
            $input['description'] ?? null
        ]);
        $stmt = $db->prepare("SELECT * FROM operator_plans WHERE id = ?");
        $stmt->execute([$id]);
        jsonResponse($stmt->fetch(), 201);
        break;

    // Operator Subscribers CRUD
    case $method === 'GET' && $path === '/operator/subscribers':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT * FROM subscribers WHERE operator_id = ? AND deleted_at IS NULL ORDER BY created_at DESC");
        $stmt->execute([$user['operator_id']]);
        jsonResponse($stmt->fetchAll());
        break;
    
    case $method === 'POST' && $path === '/operator/subscribers':
        $user = requireOperator();
        
        // Get plan name
        $stmt = $db->prepare("SELECT name FROM operator_plans WHERE id = ?");
        $stmt->execute([$input['plan_id']]);
        $plan = $stmt->fetch();
        
        $id = generateUUID();
        $stmt = $db->prepare("INSERT INTO subscribers (id, operator_id, name, whatsapp_number, email, address, plan_id, plan_name, billing_date, discount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->execute([
            $id,
            $user['operator_id'],
            $input['name'],
            $input['whatsapp_number'],
            $input['email'] ?? null,
            $input['address'] ?? null,
            $input['plan_id'],
            $plan['name'] ?? null,
            $input['billing_date'],
            $input['discount'] ?? 0
        ]);
        $stmt = $db->prepare("SELECT * FROM subscribers WHERE id = ?");
        $stmt->execute([$id]);
        jsonResponse($stmt->fetch(), 201);
        break;

    // Operator Invoices
    case $method === 'GET' && $path === '/operator/invoices':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT * FROM invoices WHERE operator_id = ? AND deleted_at IS NULL ORDER BY created_at DESC");
        $stmt->execute([$user['operator_id']]);
        jsonResponse($stmt->fetchAll());
        break;
    
    case $method === 'POST' && $path === '/operator/invoices':
        $user = requireOperator();
        
        // Get subscriber and plan
        $stmt = $db->prepare("SELECT name FROM subscribers WHERE id = ?");
        $stmt->execute([$input['subscriber_id']]);
        $subscriber = $stmt->fetch();
        
        $stmt = $db->prepare("SELECT * FROM operator_plans WHERE id = ?");
        $stmt->execute([$input['plan_id']]);
        $plan = $stmt->fetch();
        
        // Get operator for GST
        $stmt = $db->prepare("SELECT charge_gst FROM operators WHERE id = ?");
        $stmt->execute([$user['operator_id']]);
        $operator = $stmt->fetch();
        
        $baseAmount = $input['base_amount'];
        $discount = $input['discount'] ?? 0;
        $taxAmount = 0;
        
        if ($operator['charge_gst'] && ($plan['tax_percentage'] ?? 0) > 0) {
            if ($plan['tax_type'] === 'exclusive') {
                $taxAmount = ($baseAmount - $discount) * ($plan['tax_percentage'] / 100);
            } elseif ($plan['tax_type'] === 'inclusive') {
                $taxAmount = ($baseAmount - $discount) - (($baseAmount - $discount) / (1 + $plan['tax_percentage'] / 100));
            }
        }
        
        $finalAmount = $baseAmount - $discount + ($plan['tax_type'] === 'exclusive' ? $taxAmount : 0);
        
        $id = generateUUID();
        $invoiceNumber = generateInvoiceNumber($user['operator_id']);
        
        $stmt = $db->prepare("INSERT INTO invoices (id, operator_id, invoice_number, subscriber_id, subscriber_name, plan_id, plan_name, base_amount, discount, tax_amount, final_amount, service_start_date, service_end_date, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->execute([
            $id,
            $user['operator_id'],
            $invoiceNumber,
            $input['subscriber_id'],
            $subscriber['name'] ?? null,
            $input['plan_id'],
            $plan['name'] ?? null,
            $baseAmount,
            $discount,
            round($taxAmount, 2),
            round($finalAmount, 2),
            $input['service_start_date'],
            $input['service_end_date'],
            $input['due_date']
        ]);
        
        $stmt = $db->prepare("SELECT * FROM invoices WHERE id = ?");
        $stmt->execute([$id]);
        jsonResponse($stmt->fetch(), 201);
        break;

    // Operator Reports
    case $method === 'GET' && $path === '/operator/reports/revenue':
        $user = requireOperator();
        $startDate = $_GET['start_date'] ?? null;
        $endDate = $_GET['end_date'] ?? null;
        
        $sql = "SELECT COUNT(*) as total_invoices, COALESCE(SUM(final_amount), 0) as total_revenue, COALESCE(SUM(base_amount), 0) as total_base_amount, COALESCE(SUM(tax_amount), 0) as total_tax, COALESCE(SUM(discount), 0) as total_discount FROM invoices WHERE operator_id = ? AND status = 'paid' AND deleted_at IS NULL";
        $params = [$user['operator_id']];
        
        if ($startDate) {
            $sql .= " AND DATE(created_at) >= ?";
            $params[] = $startDate;
        }
        if ($endDate) {
            $sql .= " AND DATE(created_at) <= ?";
            $params[] = $endDate;
        }
        
        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        jsonResponse($stmt->fetch());
        break;

    case $method === 'GET' && $path === '/operator/reports/gst-summary':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT COALESCE(SUM(base_amount - discount), 0) as total_taxable_amount, COALESCE(SUM(tax_amount), 0) as total_gst_collected FROM invoices WHERE operator_id = ? AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        $result = $stmt->fetch();
        $result['cgst'] = round($result['total_gst_collected'] / 2, 2);
        $result['sgst'] = round($result['total_gst_collected'] / 2, 2);
        jsonResponse($result);
        break;

    case $method === 'GET' && $path === '/operator/reports/pending-overdue':
        $user = requireOperator();
        
        $stmt = $db->prepare("SELECT COUNT(*) as pending_count, COALESCE(SUM(final_amount), 0) as pending_amount FROM invoices WHERE operator_id = ? AND status = 'pending' AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        $pending = $stmt->fetch();
        
        $stmt = $db->prepare("SELECT COUNT(*) as overdue_count, COALESCE(SUM(final_amount), 0) as overdue_amount FROM invoices WHERE operator_id = ? AND status = 'overdue' AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        $overdue = $stmt->fetch();
        
        jsonResponse(array_merge($pending, $overdue));
        break;

    // Operator Staff
    case $method === 'GET' && $path === '/operator/staff':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT id, email, name, phone, role, permissions, status, created_at FROM users WHERE operator_id = ? AND role = 'staff' AND deleted_at IS NULL");
        $stmt->execute([$user['operator_id']]);
        jsonResponse($stmt->fetchAll());
        break;
    
    case $method === 'POST' && $path === '/operator/staff':
        $user = requireOperator();
        
        // Check email uniqueness
        $stmt = $db->prepare("SELECT id FROM users WHERE email = ? AND deleted_at IS NULL");
        $stmt->execute([$input['email']]);
        if ($stmt->fetch()) {
            jsonResponse(['error' => 'Email already registered'], 400);
        }
        
        $id = generateUUID();
        $stmt = $db->prepare("INSERT INTO users (id, email, name, phone, password, role, operator_id, permissions, status) VALUES (?, ?, ?, ?, ?, 'staff', ?, ?, 'active')");
        $stmt->execute([
            $id,
            $input['email'],
            $input['name'],
            $input['phone'] ?? null,
            hashPassword($input['password']),
            $user['operator_id'],
            json_encode($input['permissions'] ?? [])
        ]);
        
        jsonResponse(['id' => $id, 'email' => $input['email'], 'name' => $input['name'], 'role' => 'staff'], 201);
        break;

    // Payment Gateway Config
    case $method === 'GET' && $path === '/operator/payment-gateway':
        $user = requireOperator();
        $stmt = $db->prepare("SELECT gateway_type, CONCAT(LEFT(api_key, 8), '****') as api_key, is_active FROM payment_gateways WHERE operator_id = ?");
        $stmt->execute([$user['operator_id']]);
        $gateway = $stmt->fetch();
        if ($gateway) {
            jsonResponse(['configured' => true] + $gateway);
        } else {
            jsonResponse(['configured' => false]);
        }
        break;
    
    case $method === 'POST' && $path === '/operator/payment-gateway':
        $user = requireOperator();
        $stmt = $db->prepare("INSERT INTO payment_gateways (id, operator_id, gateway_type, api_key, api_secret, webhook_secret) VALUES (?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE gateway_type = VALUES(gateway_type), api_key = VALUES(api_key), api_secret = VALUES(api_secret), webhook_secret = VALUES(webhook_secret)");
        $stmt->execute([
            generateUUID(),
            $user['operator_id'],
            $input['gateway_type'],
            $input['api_key'],
            $input['api_secret'],
            $input['webhook_secret'] ?? null
        ]);
        jsonResponse(['message' => 'Payment gateway configured successfully']);
        break;

    // Default - 404
    default:
        jsonResponse(['error' => 'Not found', 'path' => $path], 404);
}
