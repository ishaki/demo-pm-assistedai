/**
 * Get label for PM status
 */
export const getPMStatusLabel = (pmStatus) => {
  switch (pmStatus) {
    case 'scheduled':
      return 'Scheduled';
    case 'overdue':
      return 'Overdue';
    case 'due_soon':
      return 'Due Soon';
    case 'ok':
      return 'OK';
    default:
      return 'Unknown';
  }
};

/**
 * Get label for work order status
 */
export const getWorkOrderStatusLabel = (status) => {
  switch (status) {
    case 'Pending_Approval':
      return 'Pending Approval';
    default:
      return status;
  }
};

/**
 * Get label for AI decision
 */
export const getDecisionLabel = (decision) => {
  switch (decision) {
    case 'CREATE_WORK_ORDER':
      return 'Create Work Order';
    case 'SEND_NOTIFICATION':
      return 'Send Notification';
    case 'WAIT':
      return 'Wait';
    default:
      return decision;
  }
};

/**
 * Get confidence level label
 */
export const getConfidenceLevel = (confidence) => {
  if (confidence >= 0.9) return 'Very High';
  if (confidence >= 0.7) return 'High';
  if (confidence >= 0.5) return 'Medium';
  return 'Low';
};

// ========================================
// Tailwind Badge Variant Functions
// ========================================

/**
 * Get Badge variant for PM status (Tailwind)
 */
export const getPMStatusVariant = (pmStatus) => {
  switch (pmStatus) {
    case 'scheduled':
      return 'info';
    case 'overdue':
      return 'error';
    case 'due_soon':
      return 'warning';
    case 'ok':
      return 'success';
    default:
      return 'default';
  }
};

/**
 * Get Badge variant for work order status (Tailwind)
 */
export const getWorkOrderStatusVariant = (status) => {
  switch (status) {
    case 'Draft':
      return 'default';
    case 'Pending_Approval':
      return 'warning';
    case 'Approved':
      return 'info';
    case 'Completed':
      return 'success';
    case 'Cancelled':
      return 'error';
    default:
      return 'default';
  }
};

/**
 * Get Badge variant for priority (Tailwind)
 */
export const getPriorityVariant = (priority) => {
  switch (priority) {
    case 'High':
      return 'error';
    case 'Medium':
      return 'warning';
    case 'Low':
      return 'info';
    default:
      return 'default';
  }
};

/**
 * Get Badge variant for AI decision (Tailwind)
 */
export const getDecisionVariant = (decision) => {
  switch (decision) {
    case 'CREATE_WORK_ORDER':
      return 'error';
    case 'SEND_NOTIFICATION':
      return 'warning';
    case 'WAIT':
      return 'success';
    default:
      return 'default';
  }
};

/**
 * Get Badge variant for confidence (Tailwind)
 */
export const getConfidenceVariant = (confidence) => {
  if (confidence >= 0.7) return 'success';
  if (confidence >= 0.5) return 'warning';
  return 'error';
};
