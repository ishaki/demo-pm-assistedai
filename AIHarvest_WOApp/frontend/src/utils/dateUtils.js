import { format, formatDistanceToNow, isAfter, parseISO, startOfDay } from 'date-fns';

/**
 * Format date to readable string
 */
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return format(date, 'MMM dd, yyyy');
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateString;
  }
};

/**
 * Format datetime to readable string
 */
export const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return format(date, 'MMM dd, yyyy HH:mm');
  } catch (error) {
    console.error('Error formatting datetime:', error);
    return dateString;
  }
};

/**
 * Get relative time string (e.g., "2 days ago")
 */
export const getRelativeTime = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    console.error('Error getting relative time:', error);
    return dateString;
  }
};

/**
 * Calculate days until PM date
 */
export const getDaysUntilPM = (nextPmDate) => {
  if (!nextPmDate) return null;
  try {
    const pmDate = typeof nextPmDate === 'string' ? parseISO(nextPmDate) : nextPmDate;
    const today = new Date();
    const diffTime = pmDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  } catch (error) {
    console.error('Error calculating days until PM:', error);
    return null;
  }
};

/**
 * Get PM status based on days until PM
 */
export const getPMStatus = (daysUntilPM) => {
  if (daysUntilPM === null || daysUntilPM === undefined) return 'unknown';
  if (daysUntilPM < 0) return 'overdue';
  if (daysUntilPM <= 30) return 'due_soon';
  return 'ok';
};

/**
 * Format days until PM for display
 */
export const formatDaysUntilPM = (daysUntilPM) => {
  if (daysUntilPM === null || daysUntilPM === undefined) return 'N/A';
  if (daysUntilPM < 0) {
    return `${Math.abs(daysUntilPM)} days overdue`;
  }
  if (daysUntilPM === 0) {
    return 'Due today';
  }
  return `${daysUntilPM} days`;
};

/**
 * Has a scheduled date arrived yet (is it today or earlier)?
 *
 * Compares whole days, so something scheduled for today counts as arrived
 * regardless of the time. Returns false for a missing or unparseable date:
 * callers use this to gate an action, and withholding one is safer than
 * offering an action that downstream validation will reject anyway.
 */
export const hasDateArrived = (dateString) => {
  if (!dateString) return false;
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return !isAfter(startOfDay(date), startOfDay(new Date()));
  } catch (error) {
    console.error('Error comparing date:', error);
    return false;
  }
};
