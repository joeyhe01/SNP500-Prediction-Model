import { format, parseISO } from 'date-fns';

// Utility function to parse timestamps (handles both ISO strings and Unix timestamps)
export const parseTimestamp = (timestamp) => {
  // Handle null, undefined, empty string
  if (!timestamp && timestamp !== 0) {
    console.debug('parseTimestamp received falsy value:', timestamp);
    return new Date();
  }
  
  let date;
  
  // If it's a number, treat as Unix timestamp
  if (typeof timestamp === 'number') {
    // Validate reasonable range for Unix timestamp
    if (timestamp > 946684800 && timestamp < 4102444800) {
      date = new Date(timestamp * 1000); // Convert to milliseconds
    } else if (timestamp > 946684800000 && timestamp < 4102444800000) {
      // Already in milliseconds
      date = new Date(timestamp);
    } else {
      console.warn('Numeric timestamp out of reasonable range:', timestamp);
      date = new Date();
    }
  }
  // If it's a string that looks like a Unix timestamp (all digits, reasonable length)
  else if (typeof timestamp === 'string' && /^\d{8,13}$/.test(timestamp)) {
    const unixTime = parseInt(timestamp);
    // Check if it's in seconds (8-11 digits) or milliseconds (12-13 digits)
    if (unixTime > 946684800 && unixTime < 4102444800) {
      date = new Date(unixTime * 1000); // Convert from seconds
    } else if (unixTime > 946684800000 && unixTime < 4102444800000) {
      date = new Date(unixTime); // Already in milliseconds
    } else {
      console.warn('String Unix timestamp out of reasonable range:', timestamp);
      date = new Date();
    }
  }
  // Otherwise, try to parse as ISO string
  else {
    try {
      const timestampStr = timestamp.toString().trim();
      if (timestampStr === '') {
        console.warn('Empty timestamp string');
        date = new Date();
      } else {
        date = parseISO(timestampStr);
      }
    } catch (e) {
      console.warn('Failed to parse timestamp as ISO:', timestamp, e);
      date = new Date();
    }
  }
  
  // Validate the resulting date is valid
  if (isNaN(date.getTime())) {
    console.warn('Invalid date created from timestamp:', {
      original: timestamp,
      type: typeof timestamp,
      value: timestamp
    });
    return new Date();
  }
  
  return date;
};

// Format timestamp with timezone info
export const formatTimestampWithTimezone = (timestamp, formatString = 'MMM dd, yyyy h:mm a') => {
  try {
    const date = parseTimestamp(timestamp);
    
    // Double-check the date is valid before formatting
    if (isNaN(date.getTime())) {
      console.warn('Invalid date in formatTimestampWithTimezone:', timestamp);
      return 'Invalid date';
    }
    
    const formatted = format(date, formatString);
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const offset = -date.getTimezoneOffset() / 60;
    const offsetStr = `UTC${offset >= 0 ? '+' : ''}${offset}`;
    
    return `${formatted} (${timezone}, ${offsetStr})`;
  } catch (error) {
    console.error('Error formatting timestamp:', timestamp, error);
    return 'Invalid date';
  }
};

// Format timestamp without timezone info (shorter format)
export const formatTimestamp = (timestamp, formatString = 'MMM dd h:mm a') => {
  try {
    const date = parseTimestamp(timestamp);
    
    // Double-check the date is valid before formatting
    if (isNaN(date.getTime())) {
      console.warn('Invalid date in formatTimestamp:', timestamp);
      return 'Invalid date';
    }
    
    return format(date, formatString);
  } catch (error) {
    console.error('Error formatting timestamp:', timestamp, error);
    return 'Invalid date';
  }
};

// Get timezone information
export const getTimezoneInfo = () => {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const offset = -new Date().getTimezoneOffset() / 60;
  const offsetStr = `UTC${offset >= 0 ? '+' : ''}${offset}`;
  
  return {
    timezone,
    offset,
    offsetStr,
    display: `${timezone} (${offsetStr})`
  };
};

// Debug function to help identify timestamp issues
export const debugTimestamp = (timestamp, context = '') => {
  console.log(`[DEBUG ${context}] Timestamp analysis:`, {
    original: timestamp,
    type: typeof timestamp,
    value: timestamp,
    isNumber: typeof timestamp === 'number',
    isString: typeof timestamp === 'string',
    stringLength: typeof timestamp === 'string' ? timestamp.length : 'N/A',
    parsedDate: parseTimestamp(timestamp),
    isValidDate: !isNaN(parseTimestamp(timestamp).getTime())
  });
}; 